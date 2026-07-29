from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import InstitutionMembership, InstitutionRole, User

from ..domain.enums import (
    JourneyAuthorityProviderType,
    LearningCompetencyProgressState,
    LearningCompetencyUnlockState,
    LearningJourneyActionCode,
    LearningJourneyActionReceiptStatus,
    LearningJourneyCommandResult,
    LearningJourneyIntegrityFindingCode,
    LearningJourneyIntegrityFindingStatus,
    LearningJourneyIntegritySeverity,
    LearningJourneyOperationStatus,
    LearningJourneySourceType,
    LearningJourneyStatus,
    LearningJourneySubjectBindingStatus,
    LearningJourneyType,
)
from ..domain.models import (
    InstitutionalInterventionRecommendation,
    InstitutionalLearningAssignment,
    LearningCompetencyProgress,
    LearningJourney,
    LearningJourneyActionReceipt,
    LearningJourneyIntegrityFinding,
    LearningJourneyOperation,
    LearningJourneySourceBinding,
)
from .action_policy import ACTION_COPY, SELF_STUDY_ACTIONS, SelfStudyJourneyActionPolicy
from .authority import INSTITUTION_STAFF_ROLES, JourneyAuthorityResolver
from .institutional_services import InstitutionalCompletionService
from .progression_services import DEMONSTRATED_STATES, CompetencyProgressSnapshotService
from .services import SynchronizeLearningJourneyService, can_read_journey


ACTIVE_OPERATION_STATUSES = {
    LearningJourneyOperationStatus.PENDING,
    LearningJourneyOperationStatus.RUNNING,
}

TERMINAL_JOURNEY_STATUSES = {
    LearningJourneyStatus.LEARNING_GOAL_COMPLETED,
    LearningJourneyStatus.WITHDRAWN,
    LearningJourneyStatus.ARCHIVED,
}


def _event(events: EventPublisher, name: str, payload: dict):
    events.publish(BusinessEvent.create(name, payload=payload))


def stable_payload_hash(payload: dict | None) -> str:
    material = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LearningJourneyViewPolicy:
    actor: User
    journey: LearningJourney

    @property
    def role(self) -> str:
        if self.actor.is_superuser:
            return "PLATFORM_ADMINISTRATOR"
        if self.actor.id == self.journey.learner_id:
            return "LEARNER"
        if self.journey.institution_id:
            membership = InstitutionMembership.objects.filter(
                user=self.actor,
                institution_id=self.journey.institution_id,
                is_active=True,
            ).first()
            if membership and membership.role in {
                InstitutionRole.ADMINISTRATOR,
                InstitutionRole.INSTITUTION_OWNER,
                InstitutionRole.SYSTEM_ADMINISTRATOR,
            }:
                return "INSTITUTIONAL_ADMINISTRATOR"
            if membership and membership.role in INSTITUTION_STAFF_ROLES:
                return "INSTITUTIONAL_EDUCATOR"
        return "UNAUTHORIZED"

    def visible_interventions(self):
        if self.role in {"PLATFORM_ADMINISTRATOR", "INSTITUTIONAL_ADMINISTRATOR", "INSTITUTIONAL_EDUCATOR"}:
            return InstitutionalInterventionRecommendation.objects.filter(journey=self.journey).order_by("-created_at")
        if self.role == "LEARNER":
            return InstitutionalInterventionRecommendation.objects.none()
        return InstitutionalInterventionRecommendation.objects.none()

    def include_integrity(self) -> bool:
        return self.role in {"PLATFORM_ADMINISTRATOR", "INSTITUTIONAL_ADMINISTRATOR"}

    def visible_actions(self, actions: list[dict]) -> list[dict]:
        if self.role == "UNAUTHORIZED":
            return []
        if self.role == "LEARNER":
            hidden = {"SYNCHRONIZE"}
            return [action for action in actions if action["code"] not in hidden]
        return actions


class LearningJourneyOperationalViewService:
    projection_version = "pi-8b.5.v1"

    def execute(self, *, journey_id, actor: User) -> dict:
        journey = self._journey(journey_id)
        if not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        return self.present(journey=journey, actor=actor)

    def present(self, *, journey: LearningJourney, actor: User) -> dict:
        from .queries import LearningJourneyReadPresenter

        base = LearningJourneyReadPresenter().present_legacy(journey)
        view_policy = LearningJourneyViewPolicy(actor=actor, journey=journey)
        active_binding = journey.subject_bindings.select_related("subject", "curriculum_reference").filter(status=LearningJourneySubjectBindingStatus.ACTIVE).first()
        competency_progress = self._competency_progress(journey=journey)
        active_context = self._active_context(base=base, competency_progress=competency_progress, journey=journey, view_policy=view_policy)
        available_actions = view_policy.visible_actions([self._operational_action(action) for action in base["available_actions"]])
        blockers = self._dedupe_blockers([self._operational_blocker(blocker) for blocker in base["blockers"]])
        authority = self._authority(base=base, journey=journey, active_binding=active_binding)
        payload = {
            **base,
            "status": base["state"],
            "status_reason": self._status_reason(base["status_reason"]),
            "authority": authority,
            "learner": {
                "id": str(journey.learner_id),
                "display_name": getattr(journey.learner, "get_full_name", lambda: "")() or getattr(journey.learner, "email", ""),
            },
            "subject": base.get("subject"),
            "current_step": self._current_step(base["current_step"], base["available_actions"]),
            "progress": self._progress(base=base, competency_progress=competency_progress, journey=journey),
            "active_context": active_context,
            "available_actions": available_actions,
            "blockers": blockers,
            "recent_activity": self._recent_activity(journey=journey),
            "operational_metadata": self._metadata(journey=journey),
            "view_policy": {"role": view_policy.role},
        }
        return payload

    def _journey(self, journey_id):
        return (
            LearningJourney.objects.select_related("learner", "institution")
            .prefetch_related("source_bindings", "subject_bindings", "action_receipts", "operations", "integrity_findings")
            .get(id=journey_id)
        )

    def _status_reason(self, status_reason: dict) -> dict:
        message = status_reason.get("message") or self._reason_messages().get(status_reason.get("code"), "Your learning journey is being prepared.")
        return {"code": status_reason.get("code", "UNKNOWN"), "message": message}

    def _reason_messages(self) -> dict:
        return {
            "JOURNEY_CREATED": "Your learning journey has been created.",
            "INTENT_NOT_CONFIRMED": "Your study goal still needs to be shaped.",
            "CURRICULUM_SELECTION_REQUIRED": "A governed curriculum match is ready for selection.",
            "SELF_STUDY_BINDING_MISSING": "This curriculum is verified, but it is not yet available for self-study.",
            "DIAGNOSTIC_REQUIRED": "A starting check will help place your learning plan.",
            "LEARNING_PLAN_REQUIRED": "Your learning plan needs to be prepared.",
            "TEACHING_NOT_READY": "Teaching material is still being prepared.",
            "MANUALLY_PAUSED": "This journey is paused.",
            "GOAL_COMPLETED": "This journey goal is complete.",
        }

    def _authority(self, *, base: dict, journey: LearningJourney, active_binding) -> dict:
        authority = dict(base.get("authority") or {})
        authority_type = authority.get("type") or (JourneyAuthorityProviderType.INSTITUTION if journey.journey_type == LearningJourneyType.INSTITUTIONAL else JourneyAuthorityProviderType.SELF_STUDY)
        authority.setdefault("type", authority_type)
        authority["learner_controlled"] = authority_type == JourneyAuthorityProviderType.SELF_STUDY
        authority.setdefault("institution_id", str(journey.institution_id or "") or None)
        if journey.institution_id and journey.institution:
            authority.setdefault("institution_name", journey.institution.name)
        if active_binding:
            authority.setdefault("curriculum_reference_id", str(active_binding.curriculum_reference_id or "") or None)
            authority.setdefault("curriculum_name", active_binding.curriculum_reference.title if active_binding.curriculum_reference_id else "")
            authority.setdefault("subject_binding_source", active_binding.binding_source)
        assignment = InstitutionalLearningAssignment.objects.select_related("institution", "membership", "curriculum_reference").filter(journey=journey).first()
        if assignment:
            authority.update(
                {
                    "type": JourneyAuthorityProviderType.INSTITUTION,
                    "learner_controlled": False,
                    "institution_id": str(assignment.institution_id),
                    "institution_name": assignment.institution.name,
                    "membership_id": str(assignment.membership_id),
                    "assignment_id": str(assignment.id),
                    "curriculum_reference_id": str(assignment.curriculum_reference_id or "") or None,
                    "curriculum_name": assignment.curriculum_reference.title if assignment.curriculum_reference_id else "",
                    "programme": assignment.programme_label,
                    "course": assignment.course_label,
                }
            )
        return authority

    def _current_step(self, current_step: dict, available_actions: list[dict]) -> dict:
        primary = next((action for action in available_actions if action.get("enabled")), None) or (available_actions[0] if available_actions else None)
        phase = self._phase_for_step(current_step.get("code", ""))
        return {
            **current_step,
            "phase": phase,
            "is_terminal": current_step.get("code") == "GOAL_COMPLETED",
            "primary_action_code": primary["code"] if primary else "",
        }

    def _phase_for_step(self, code: str) -> str:
        return {
            "DISCOVER_GOAL": "GOAL_DISCOVERY",
            "CONFIRM_INTENT": "GOAL_DISCOVERY",
            "RESOLVE_CURRICULUM": "CURRICULUM",
            "SELECT_CURRICULUM": "CURRICULUM",
            "WAIT_FOR_SUBJECT_BINDING": "CURRICULUM",
            "COMPLETE_ENTRY_DIAGNOSTIC": "STARTING_STATE",
            "REVIEW_PLACEMENT": "STARTING_STATE",
            "COMPLETE_BRIDGE": "BRIDGE",
            "CREATE_LEARNING_PLAN": "PLANNING",
            "BEGIN_LEARNING": "LEARNING",
            "CONTINUE_LEARNING": "LEARNING",
            "RESOLVE_BLOCKER": "LEARNING",
            "REVIEW_PROGRESS": "PROGRESS",
            "GOAL_COMPLETED": "COMPLETED",
        }.get(code, "OPERATIONAL")

    def _competency_progress(self, *, journey: LearningJourney) -> dict:
        try:
            return CompetencyProgressSnapshotService().journey_progress(journey_id=journey.id, actor=journey.learner)
        except Exception:
            return {
                "current_learning_phase": "NOT_STARTED",
                "active_competency": None,
                "next_competency": None,
                "blocked_competencies": [],
                "available_competencies": [],
                "completed_competency_count": 0,
            }

    def _progress(self, *, base: dict, competency_progress: dict, journey: LearningJourney) -> dict:
        rows = LearningCompetencyProgress.objects.filter(journey=journey)
        return {
            "phase": base.get("progress", {}).get("phase", competency_progress["current_learning_phase"]),
            "workflow": {
                "completed_steps": base.get("progress", {}).get("completed_steps", 0),
                "known_steps": base.get("progress", {}).get("total_known_steps", 0),
                "conditional": not base.get("progress", {}).get("is_exact_total", False),
            },
            "competencies": {
                "active": rows.filter(unlock_state=LearningCompetencyUnlockState.ACTIVE).count(),
                "demonstrated": rows.filter(state=LearningCompetencyProgressState.DEMONSTRATED).count(),
                "reinforced": rows.filter(state=LearningCompetencyProgressState.REINFORCED).count(),
                "review_required": rows.filter(state=LearningCompetencyProgressState.REVIEW_REQUIRED).count(),
                "locked": rows.filter(unlock_state=LearningCompetencyUnlockState.LOCKED).count(),
            },
            "active_competency": competency_progress.get("active_competency"),
            "next_competencies": competency_progress.get("available_competencies", [])[:5],
            "completion_readiness": self._completion_readiness(journey=journey),
        }

    def _completion_readiness(self, *, journey: LearningJourney) -> dict:
        assignment = InstitutionalLearningAssignment.objects.filter(journey=journey).first()
        if assignment:
            return {"state": assignment.completion_state, "assignment_id": str(assignment.id)}
        return {"state": "NOT_APPLICABLE"}

    def _active_context(self, *, base: dict, competency_progress: dict, journey: LearningJourney, view_policy: LearningJourneyViewPolicy) -> dict:
        refs = base.get("active_capabilities") or {}
        intervention = view_policy.visible_interventions().filter(status__in=["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]).first()
        operation = LearningJourneyOperation.objects.filter(journey=journey, status__in=ACTIVE_OPERATION_STATUSES).order_by("-started_at").first()
        return {
            "learning_plan": {"id": refs.get("learning_plan_id"), "status": "ACTIVE"} if refs.get("learning_plan_id") else None,
            "bridge_plan": {"id": refs.get("bridge_plan_id"), "status": "ACTIVE"} if refs.get("bridge_plan_id") else None,
            "teaching_preparation": {"id": refs.get("teaching_preparation_id"), "status": "ACTIVE"} if refs.get("teaching_preparation_id") else None,
            "teaching_session": {"id": refs.get("active_teaching_session_id"), "status": "ACTIVE", "resumable": True}
            if refs.get("active_teaching_session_id")
            else None,
            "diagnostic": {"id": refs.get("diagnostic_id"), "status": "ACTIVE"} if refs.get("diagnostic_id") else None,
            "remediation": {"id": refs.get("remediation_plan_id"), "status": "ACTIVE"} if refs.get("remediation_plan_id") else None,
            "active_competency": competency_progress.get("active_competency") or competency_progress.get("next_competency"),
            "intervention": self._intervention_row(intervention) if intervention else None,
            "operation": self._operation_row(operation) if operation else None,
        }

    def _operational_action(self, action: dict) -> dict:
        disabled_reason = action.get("disabled_reason") or ""
        return {
            "code": action["code"],
            "label": action.get("label") or ACTION_COPY.get(action["code"], action["code"].replace("_", " ").title()),
            "description": self._action_descriptions().get(action["code"], ""),
            "enabled": bool(action.get("enabled")),
            "disabled_reason": {"code": "ACTION_NOT_AVAILABLE", "message": disabled_reason} if disabled_reason else None,
            "requires_confirmation": bool(action.get("requires_confirmation")),
            "payload_schema": self._payload_schema(action["code"]),
            "execution_mode": self._execution_mode(action),
            "method": action.get("method", "POST"),
            "endpoint_name": action.get("endpoint_name", ""),
        }

    def _action_descriptions(self) -> dict:
        return {
            "BEGIN_GOAL_DISCOVERY": "Start shaping the learner's study goal.",
            "CONTINUE_GOAL_DISCOVERY": "Continue the governed setup conversation.",
            "RESOLVE_CURRICULUM": "Find a governed curriculum match.",
            "SELECT_CURRICULUM": "Select an eligible governed curriculum candidate.",
            "BEGIN_DIAGNOSTIC": "Start the governed starting check.",
            "CONFIRM_PLACEMENT": "Confirm the learner's starting point.",
            "BEGIN_TEACHING_SESSION": "Start the next prepared learning session.",
            "CONTINUE_TEACHING_SESSION": "Resume the active teaching session.",
            "SYNCHRONIZE": "Refresh the derived journey projection.",
        }

    def _payload_schema(self, code: str) -> dict:
        if code == LearningJourneyActionCode.WITHDRAW_JOURNEY:
            return {"type": "object", "required": ["confirmation"], "properties": {"confirmation": {"const": "WITHDRAW"}}}
        if code == LearningJourneyActionCode.SELECT_CURRICULUM:
            return {"type": "object", "required": ["candidate_id"], "properties": {"candidate_id": {"type": "string"}}}
        return {"type": "object"}

    def _execution_mode(self, action: dict) -> str:
        if action.get("requires_confirmation"):
            return "REQUIRES_CONFIRMATION"
        if action.get("code") in {
            LearningJourneyActionCode.RESOLVE_CURRICULUM,
            LearningJourneyActionCode.GENERATE_BRIDGE_PLAN,
            LearningJourneyActionCode.GENERATE_LEARNING_PLAN,
            LearningJourneyActionCode.PREPARE_TEACHING_SESSION,
        }:
            return "LONG_RUNNING"
        return "IMMEDIATE"

    def _operational_blocker(self, blocker: dict) -> dict:
        return {
            "code": blocker.get("code", "UNKNOWN_BLOCKER"),
            "category": blocker.get("category", "OPERATIONAL"),
            "severity": "BLOCKING" if blocker.get("recoverable") is False else "WARNING",
            "title": blocker.get("code", "Blocker").replace("_", " ").title(),
            "message": blocker.get("message", "This journey cannot continue yet."),
            "recoverable": bool(blocker.get("recoverable")),
            "resolution_action_code": blocker.get("resolution_action_code", ""),
            "source_capability": blocker.get("blocking_capability", ""),
            "detected_at": None,
        }

    def _dedupe_blockers(self, blockers: list[dict]) -> list[dict]:
        seen: dict[tuple[str, str], dict] = {}
        for blocker in blockers:
            key = (blocker["code"], blocker["category"])
            if key not in seen:
                seen[key] = blocker
            else:
                supporting = seen[key].setdefault("supporting_sources", [])
                if blocker.get("source_capability") and blocker["source_capability"] not in supporting:
                    supporting.append(blocker["source_capability"])
        return list(seen.values())

    def _recent_activity(self, *, journey: LearningJourney) -> list[dict]:
        rows = journey.action_receipts.order_by("-started_at")[:10]
        activity = []
        for receipt in rows:
            activity.append(
                {
                    "event_code": self._activity_code(receipt.action_code, receipt.status),
                    "title": ACTION_COPY.get(receipt.action_code, receipt.action_code.replace("_", " ").title()),
                    "occurred_at": receipt.completed_at.isoformat() if receipt.completed_at else receipt.started_at.isoformat(),
                    "source_type": "ACTION_RECEIPT",
                    "source_id": str(receipt.id),
                }
            )
        if not activity:
            activity.append(
                {
                    "event_code": "JOURNEY_CREATED",
                    "title": "Journey created",
                    "occurred_at": journey.created_at.isoformat(),
                    "source_type": "LEARNING_JOURNEY",
                    "source_id": str(journey.id),
                }
            )
        return activity

    def _activity_code(self, action_code: str, status: str) -> str:
        if status == LearningJourneyActionReceiptStatus.FAILED:
            return "ACTION_FAILED"
        return {
            LearningJourneyActionCode.CONFIRM_INTENT: "INTENT_CONFIRMED",
            LearningJourneyActionCode.SELECT_CURRICULUM: "CURRICULUM_SELECTED",
            LearningJourneyActionCode.BEGIN_DIAGNOSTIC: "DIAGNOSTIC_STARTED",
            LearningJourneyActionCode.CONFIRM_PLACEMENT: "PLACEMENT_CONFIRMED",
            LearningJourneyActionCode.BEGIN_TEACHING_SESSION: "SESSION_STARTED",
        }.get(action_code, "JOURNEY_ACTION")

    def _metadata(self, *, journey: LearningJourney) -> dict:
        open_findings = journey.integrity_findings.filter(status=LearningJourneyIntegrityFindingStatus.OPEN).count()
        return {
            "projection_version": self.projection_version,
            "journey_version": journey.version,
            "last_synchronized_at": journey.last_synchronized_at.isoformat() if journey.last_synchronized_at else None,
            "stale": not bool(journey.last_synchronized_at),
            "synchronization_required": not bool(journey.last_synchronized_at) or open_findings > 0,
            "etag": f'W/"journey-{journey.id}-{journey.version}-{journey.projection_version}"',
            "integrity_open_findings": open_findings,
        }

    def _intervention_row(self, row) -> dict:
        return {
            "id": str(row.id),
            "reason": row.reason,
            "severity": row.severity,
            "status": row.status,
            "recommended_action": row.recommended_action,
        }

    def _operation_row(self, row: LearningJourneyOperation | None) -> dict | None:
        if not row:
            return None
        return {
            "operation_id": str(row.id),
            "journey_id": str(row.journey_id),
            "action_code": row.action_code,
            "status": row.status,
            "progress_phase": row.progress_phase,
            "started_at": row.started_at.isoformat(),
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "failure_code": row.failure_code,
            "result_reference": row.result_reference,
        }


class LearningJourneyCollectionService:
    def execute(self, *, actor: User, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        queryset = LearningJourney.objects.select_related("learner", "institution").order_by("-updated_at")
        queryset = self._authorized_queryset(queryset=queryset, actor=actor)
        if filters.get("journey_type"):
            queryset = queryset.filter(journey_type=filters["journey_type"])
        if filters.get("status"):
            queryset = queryset.filter(status=filters["status"])
        if filters.get("institution"):
            queryset = queryset.filter(institution_id=filters["institution"])
        if filters.get("learner"):
            queryset = queryset.filter(learner_id=filters["learner"])
        if str(filters.get("active", "")).lower() in {"true", "1"}:
            queryset = queryset.exclude(status__in=TERMINAL_JOURNEY_STATUSES)
        if str(filters.get("blocked", "")).lower() in {"true", "1"}:
            queryset = queryset.filter(Q(status=LearningJourneyStatus.LEARNING_BLOCKED) | Q(integrity_findings__status=LearningJourneyIntegrityFindingStatus.OPEN)).distinct()
        if str(filters.get("completion_ready", "")).lower() in {"true", "1"}:
            queryset = queryset.filter(institutional_assignment__completion_state="READY")
        return [LearningJourneyOperationalViewService().present(journey=journey, actor=actor) for journey in queryset.distinct()]

    def active(self, *, actor: User) -> dict:
        journeys = self.execute(actor=actor, filters={"active": "true"})
        learner_journeys = [item for item in journeys if item["learner"]["id"] == str(actor.id)]
        if not learner_journeys:
            return {"result": "NONE", "journey": None, "journeys": []}
        if len(learner_journeys) == 1:
            return {"result": "ONE", "journey": learner_journeys[0], "journeys": []}
        return {"result": "MULTIPLE", "journey": None, "journeys": learner_journeys}

    def _authorized_queryset(self, *, queryset, actor: User):
        if actor.is_superuser:
            return queryset
        institution_ids = list(
            InstitutionMembership.objects.filter(user=actor, is_active=True, role__in=INSTITUTION_STAFF_ROLES).values_list("institution_id", flat=True)
        )
        return queryset.filter(Q(learner=actor) | Q(institution_id__in=institution_ids))


class LearningJourneyOperationService:
    def __init__(self, *, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def get(self, *, journey_id, operation_id, actor: User) -> dict:
        journey = LearningJourney.objects.get(id=journey_id)
        if not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        operation = LearningJourneyOperation.objects.get(id=operation_id, journey=journey)
        return {
            "operation": LearningJourneyOperationalViewService()._operation_row(operation),
            "receipt": self._receipt_row(operation.receipt) if operation.receipt_id else None,
            "journey": LearningJourneyOperationalViewService().present(journey=journey, actor=actor) if operation.status in {LearningJourneyOperationStatus.SUCCEEDED, LearningJourneyOperationStatus.FAILED, LearningJourneyOperationStatus.CANCELLED} else None,
        }

    def create_for_receipt(self, *, receipt: LearningJourneyActionReceipt, status: str = LearningJourneyOperationStatus.SUCCEEDED, phase: str = "completed") -> LearningJourneyOperation:
        operation = LearningJourneyOperation.objects.create(
            journey=receipt.journey,
            action_code=receipt.action_code,
            receipt=receipt,
            actor=receipt.actor,
            status=status,
            progress_phase=phase,
            completed_at=timezone.now() if status in {LearningJourneyOperationStatus.SUCCEEDED, LearningJourneyOperationStatus.FAILED, LearningJourneyOperationStatus.CANCELLED} else None,
            failure_code=receipt.failure_code,
            failure_message=receipt.failure_message,
            result_reference={"receipt_id": str(receipt.id), **(receipt.result_metadata or {})},
        )
        if status in {LearningJourneyOperationStatus.PENDING, LearningJourneyOperationStatus.RUNNING}:
            transaction.on_commit(lambda: _event(self.events, "learning_journey.operation_started", self._event_payload(operation)))
        elif status == LearningJourneyOperationStatus.SUCCEEDED:
            transaction.on_commit(lambda: _event(self.events, "learning_journey.operation_completed", self._event_payload(operation)))
        elif status == LearningJourneyOperationStatus.FAILED:
            transaction.on_commit(lambda: _event(self.events, "learning_journey.operation_failed", self._event_payload(operation)))
        return operation

    def _event_payload(self, operation: LearningJourneyOperation) -> dict:
        return {
            "operation_id": str(operation.id),
            "journey_id": str(operation.journey_id),
            "action_code": operation.action_code,
            "status": operation.status,
            "actor_id": str(operation.actor_id),
            "receipt_id": str(operation.receipt_id or ""),
        }

    def _receipt_row(self, receipt: LearningJourneyActionReceipt) -> dict:
        return {
            "id": str(receipt.id),
            "action_code": receipt.action_code,
            "status": receipt.status,
            "failure_code": receipt.failure_code,
            "failure_message": receipt.failure_message,
        }


class LearningJourneyIntegrityService:
    def __init__(self, *, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def check(self, *, journey_id, actor: User, repair: bool = False) -> dict:
        journey = LearningJourney.objects.select_related("learner", "institution").get(id=journey_id)
        if not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        findings = self._detect(journey=journey)
        durable = [self._open_or_refresh(journey=journey, finding=finding) for finding in findings]
        if repair:
            self._safe_repair(journey=journey, actor=actor, findings=durable)
        return {
            "journey_id": str(journey.id),
            "findings": [self._finding_row(row) for row in durable],
            "repair_attempted": repair,
        }

    def _detect(self, *, journey: LearningJourney) -> list[dict]:
        findings = []
        source_bindings = list(journey.source_bindings.all())
        if not source_bindings:
            findings.append(self._finding(LearningJourneyIntegrityFindingCode.MISSING_SOURCE_BINDING, "Journey has no source authority binding.", LearningJourneyIntegritySeverity.CRITICAL, "learning_journey.authority"))
        active_bindings = journey.subject_bindings.filter(status=LearningJourneySubjectBindingStatus.ACTIVE)
        if active_bindings.count() > 1:
            findings.append(self._finding(LearningJourneyIntegrityFindingCode.DUPLICATE_ACTIVE_SUBJECT_BINDING, "Journey has more than one active subject binding.", LearningJourneyIntegritySeverity.CRITICAL, "learning_journey.subject_binding"))
        if journey.journey_type == LearningJourneyType.INSTITUTIONAL and not InstitutionalLearningAssignment.objects.filter(journey=journey).exists():
            findings.append(
                self._finding(
                    LearningJourneyIntegrityFindingCode.INSTITUTIONAL_JOURNEY_WITHOUT_ACTIVE_AUTHORITY,
                    "Institutional journey has no institutional assignment authority.",
                    LearningJourneyIntegritySeverity.BLOCKING,
                    "institutional_learning.assignment",
                )
            )
        if journey.journey_type == LearningJourneyType.SELF_STUDY and journey.source_bindings.filter(source_type=LearningJourneySourceType.INSTITUTIONAL_ASSIGNMENT).exists():
            findings.append(
                self._finding(
                    LearningJourneyIntegrityFindingCode.SELF_STUDY_JOURNEY_WITH_INSTITUTIONAL_AUTHORITY,
                    "Self-study journey is bound to institutional-only authority.",
                    LearningJourneyIntegritySeverity.CRITICAL,
                    "learning_journey.authority",
                )
            )
        if journey.status in TERMINAL_JOURNEY_STATUSES and journey.operations.filter(status__in=ACTIVE_OPERATION_STATUSES).exists():
            findings.append(
                self._finding(
                    LearningJourneyIntegrityFindingCode.TERMINAL_JOURNEY_WITH_ACTIVE_OPERATION,
                    "Terminal journey still has an active operation.",
                    LearningJourneyIntegritySeverity.WARNING,
                    "learning_journey.operation",
                )
            )
        if not journey.last_synchronized_at:
            findings.append(self._finding(LearningJourneyIntegrityFindingCode.STALE_AUTHORITY_PROJECTION, "Journey projection has not been synchronized.", LearningJourneyIntegritySeverity.WARNING, "learning_journey.synchronization"))
        return findings

    def _finding(self, code: str, message: str, severity: str, source_capability: str) -> dict:
        return {"code": code, "message": message, "severity": severity, "source_capability": source_capability}

    def _open_or_refresh(self, *, journey: LearningJourney, finding: dict) -> LearningJourneyIntegrityFinding:
        row, created = LearningJourneyIntegrityFinding.objects.get_or_create(
            journey=journey,
            code=finding["code"],
            status=LearningJourneyIntegrityFindingStatus.OPEN,
            defaults={
                "severity": finding["severity"],
                "message": finding["message"],
                "source_capability": finding["source_capability"],
            },
        )
        if not created and (row.message != finding["message"] or row.severity != finding["severity"]):
            row.message = finding["message"]
            row.severity = finding["severity"]
            row.source_capability = finding["source_capability"]
            row.save(update_fields=["message", "severity", "source_capability", "updated_at"])
        if created:
            transaction.on_commit(
                lambda: _event(
                    self.events,
                    "learning_journey.integrity_finding_detected",
                    {"journey_id": str(journey.id), "finding_id": str(row.id), "code": row.code, "severity": row.severity},
                )
            )
        return row

    def _safe_repair(self, *, journey: LearningJourney, actor: User, findings: list[LearningJourneyIntegrityFinding]):
        codes = {finding.code for finding in findings}
        if LearningJourneyIntegrityFindingCode.STALE_AUTHORITY_PROJECTION in codes and journey.source_bindings.exists():
            SynchronizeLearningJourneyService().execute(journey_id=journey.id, actor=actor)
            for finding in findings:
                if finding.code == LearningJourneyIntegrityFindingCode.STALE_AUTHORITY_PROJECTION and finding.resolve(resolution="Projection synchronized."):
                    finding.save(update_fields=["status", "resolved_at", "resolution", "updated_at"])
                    transaction.on_commit(
                        lambda finding_id=str(finding.id): _event(
                            self.events,
                            "learning_journey.integrity_finding_resolved",
                            {"journey_id": str(journey.id), "finding_id": finding_id, "code": LearningJourneyIntegrityFindingCode.STALE_AUTHORITY_PROJECTION},
                        )
                    )

    def _finding_row(self, row: LearningJourneyIntegrityFinding) -> dict:
        return {
            "id": str(row.id),
            "code": row.code,
            "severity": row.severity,
            "status": row.status,
            "message": row.message,
            "source_capability": row.source_capability,
            "detected_at": row.detected_at.isoformat(),
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            "resolution": row.resolution,
        }


class LearningJourneyErrorEnvelope:
    @staticmethod
    def validation(exc: ValidationError) -> dict:
        code = getattr(exc, "code", "") or "VALIDATION_ERROR"
        if hasattr(exc, "error_list") and exc.error_list:
            code = exc.error_list[0].code or code
        message = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
        return {"error": {"code": code, "message": message, "details": {}, "recoverable": True, "resolution_action_code": ""}}
