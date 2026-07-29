from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.self_study.application.curriculum_services import ResolveCurriculumAttemptService, StartCurriculumResolutionService
from apps.self_study.application.diagnostic_services import CreateEntryDiagnosticService, DiagnosticDeliveryService, FinalizeDiagnosticPlacementService
from apps.self_study.application.onboarding_services import SelfStudyConversationalOnboardingService
from apps.self_study.diagnostic_models import DiagnosticStatus
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.domain.models import User

from ..domain.enums import LearningJourneyActionCode, LearningJourneyActionReceiptStatus, LearningJourneySourceType, LearningJourneyType
from ..domain.models import LearningJourney, LearningJourneyActionReceipt, LearningJourneySourceBinding
from .action_policy import SelfStudyJourneyActionPolicy
from .commands import ExecuteLearningJourneyActionCommand
from .invalidation import SelfStudyJourneyDependencyInvalidationPolicy
from .operational import LearningJourneyOperationService, stable_payload_hash
from .queries import GetLearningJourneyService
from .services import LearningJourneyLifecycleService, SynchronizeLearningJourneyService, can_read_journey

logger = logging.getLogger(__name__)


SAFE_PAYLOAD_KEYS = {
    "expected_version",
    "candidate_id",
    "onboarding_id",
    "diagnostic_id",
    "purpose_acknowledged",
    "confirmation",
    "reason",
}


def _publish(events: EventPublisher, name: str, receipt: LearningJourneyActionReceipt, extra: dict | None = None):
    payload = {
        "journey_id": str(receipt.journey_id),
        "receipt_id": str(receipt.id),
        "action_code": receipt.action_code,
        "actor_id": str(receipt.actor_id),
        "status": receipt.status,
    }
    payload.update(extra or {})
    events.publish(BusinessEvent.create(name, payload=payload))


def safe_request_metadata(payload: dict) -> dict:
    metadata = {key: str(value) for key, value in (payload or {}).items() if key in SAFE_PAYLOAD_KEYS and value not in (None, "")}
    metadata["payload_hash"] = stable_payload_hash(payload or {})
    return metadata


class SelfStudyJourneyOrchestrator:
    def __init__(
        self,
        *,
        events: EventPublisher | None = None,
        policy: SelfStudyJourneyActionPolicy | None = None,
    ):
        self.events = events or EventPublisher()
        self.policy = policy or SelfStudyJourneyActionPolicy()
        self.invalidation_policy = SelfStudyJourneyDependencyInvalidationPolicy()

    def execute(self, *, command: ExecuteLearningJourneyActionCommand, actor: User) -> dict:
        journey = LearningJourney.objects.select_related("learner", "institution").get(id=command.journey_id)
        if str(actor.id) != str(command.actor_id):
            raise PermissionDenied("LEARNING_JOURNEY_ACTOR_MISMATCH")
        if not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        if journey.journey_type != LearningJourneyType.SELF_STUDY:
            raise ValidationError("Journey action is only available for self-study journeys.", code="LEARNING_JOURNEY_TYPE_MISMATCH")

        existing = self._idempotent_receipt(journey=journey, action_code=command.action_code, idempotency_key=command.idempotency_key)
        if existing and existing.request_metadata.get("payload_hash") != stable_payload_hash(command.payload or {}):
            receipt = existing
            if receipt.status == LearningJourneyActionReceiptStatus.ACCEPTED:
                receipt.mark_conflict(
                    code="IDEMPOTENCY_KEY_PAYLOAD_MISMATCH",
                    message="This idempotency key was already used with a different payload.",
                    result_metadata={"current_version": journey.version},
                )
                receipt.save()
                LearningJourneyOperationService().create_for_receipt(receipt=receipt, status="FAILED", phase="idempotency_conflict")
                return self._response(receipt=receipt, journey_id=journey.id, actor=actor, replayed=True)
            return self._conflict_response(
                receipt=receipt,
                journey_id=journey.id,
                actor=actor,
                code="IDEMPOTENCY_KEY_PAYLOAD_MISMATCH",
                message="This idempotency key was already used with a different payload.",
            )
        if existing and existing.status in {
            LearningJourneyActionReceiptStatus.SUCCEEDED,
            LearningJourneyActionReceiptStatus.NO_OP,
            LearningJourneyActionReceiptStatus.REJECTED,
            LearningJourneyActionReceiptStatus.CONFLICT,
        }:
            return self._response(receipt=existing, journey_id=journey.id, actor=actor, replayed=True)

        if command.expected_journey_version and journey.version != command.expected_journey_version:
            receipt = existing or self._receipt(journey=journey, actor=actor, command=command)
            receipt.mark_conflict(
                code="JOURNEY_VERSION_CONFLICT",
                message="Journey version is stale.",
                result_metadata={"expected_version": command.expected_journey_version, "current_version": journey.version},
            )
            receipt.save()
            transaction.on_commit(lambda: _publish(self.events, "learning_journey.command_conflicted", receipt, {"failure_code": receipt.failure_code}))
            LearningJourneyOperationService().create_for_receipt(receipt=receipt, status="FAILED", phase="version_conflict")
            return self._response(receipt=receipt, journey_id=journey.id, actor=actor)

        definition = self.policy.definition(command.action_code)
        if not definition:
            receipt = self._receipt(journey=journey, actor=actor, command=command)
            receipt.mark_rejected(code="LEARNING_JOURNEY_ACTION_NOT_REGISTERED", message="Journey action is not registered.")
            receipt.save()
            transaction.on_commit(lambda: _publish(self.events, "learning_journey.action_rejected", receipt))
            LearningJourneyOperationService().create_for_receipt(receipt=receipt, status="FAILED", phase="rejected")
            return self._response(receipt=receipt, journey_id=journey.id, actor=actor)

        available, reason = self.policy.availability(journey=journey, action_code=command.action_code)
        receipt = existing or self._receipt(journey=journey, actor=actor, command=command)
        if not available:
            receipt.mark_rejected(code="LEARNING_JOURNEY_ACTION_NOT_AVAILABLE", message=reason, result_metadata={"source_capability": definition.source_capability})
            receipt.source_capability = definition.source_capability
            receipt.save()
            transaction.on_commit(lambda: _publish(self.events, "learning_journey.action_rejected", receipt))
            LearningJourneyOperationService().create_for_receipt(receipt=receipt, status="FAILED", phase="rejected")
            return self._response(receipt=receipt, journey_id=journey.id, actor=actor)

        try:
            transaction.on_commit(lambda: _publish(self.events, "learning_journey.action_accepted", receipt))
            result = self._delegate(journey=journey, actor=actor, action_code=command.action_code, payload=command.payload, idempotency_key=command.idempotency_key)
            if command.action_code in {
                LearningJourneyActionCode.PAUSE_JOURNEY,
                LearningJourneyActionCode.RESUME_JOURNEY,
                LearningJourneyActionCode.WITHDRAW_JOURNEY,
                LearningJourneyActionCode.SYNCHRONIZE,
            }:
                synchronized = LearningJourney.objects.get(id=journey.id)
            else:
                synchronized = SynchronizeLearningJourneyService(events=self.events).execute(journey_id=journey.id, actor=actor)
        except ValidationError as exc:
            code = getattr(exc, "code", "") or (exc.error_list[0].code if getattr(exc, "error_list", None) else "LEARNING_JOURNEY_ACTION_FAILED")
            message = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            receipt.mark_failed(code=code or "LEARNING_JOURNEY_ACTION_FAILED", message=message)
            receipt.save()
            transaction.on_commit(lambda: _publish(self.events, "learning_journey.action_failed", receipt, {"failure_code": receipt.failure_code}))
            LearningJourneyOperationService().create_for_receipt(receipt=receipt, status="FAILED", phase="failed")
            logger.info(
                "learning_journey.action_failed",
                extra={"journey_id": str(journey.id), "action_code": command.action_code, "receipt_id": str(receipt.id), "failure_code": receipt.failure_code},
            )
            return self._response(receipt=receipt, journey_id=journey.id, actor=actor)

        receipt.mark_succeeded(
            source_capability=definition.source_capability,
            source_record_id=result.get("source_record_id"),
            result_metadata={
                "journey_status": synchronized.status,
                "source_capability": definition.source_capability,
                **{key: value for key, value in result.items() if key != "source_record_id"},
            },
        )
        receipt.save()
        LearningJourneyOperationService().create_for_receipt(receipt=receipt, status="SUCCEEDED", phase="completed")
        transaction.on_commit(lambda: _publish(self.events, "learning_journey.action_succeeded", receipt, {"journey_status": synchronized.status}))
        milestone = self._milestone_event(command.action_code)
        if milestone:
            transaction.on_commit(lambda: _publish(self.events, milestone, receipt, receipt.result_metadata))
        logger.info(
            "learning_journey.action_succeeded",
            extra={"journey_id": str(journey.id), "action_code": command.action_code, "receipt_id": str(receipt.id), "new_status": synchronized.status},
        )
        return self._response(receipt=receipt, journey_id=journey.id, actor=actor)

    def _idempotent_receipt(self, *, journey: LearningJourney, action_code: str, idempotency_key: str) -> LearningJourneyActionReceipt | None:
        if not idempotency_key:
            return None
        return LearningJourneyActionReceipt.objects.filter(journey=journey, action_code=action_code, idempotency_key=idempotency_key).first()

    def _receipt(self, *, journey: LearningJourney, actor: User, command: ExecuteLearningJourneyActionCommand) -> LearningJourneyActionReceipt:
        try:
            return LearningJourneyActionReceipt.objects.create(
                journey=journey,
                action_code=command.action_code,
                actor=actor,
                idempotency_key=command.idempotency_key,
                request_metadata=safe_request_metadata(command.payload),
            )
        except IntegrityError:
            return LearningJourneyActionReceipt.objects.get(
                journey=journey,
                action_code=command.action_code,
                idempotency_key=command.idempotency_key,
            )

    def _workspace(self, journey: LearningJourney, actor: User) -> SelfStudyWorkspace:
        binding = LearningJourneySourceBinding.objects.get(journey=journey, source_type=LearningJourneySourceType.SELF_STUDY_WORKSPACE)
        workspace = SelfStudyWorkspace.objects.select_related("intent", "learner", "tenant", "curriculum_resolution").get(id=binding.source_id)
        if workspace.learner_id != actor.id and not actor.is_superuser:
            raise PermissionDenied("LEARNING_JOURNEY_WORKSPACE_PERMISSION_DENIED")
        return workspace

    def _delegate(self, *, journey: LearningJourney, actor: User, action_code: str, payload: dict, idempotency_key: str) -> dict:
        workspace = self._workspace(journey, actor)
        if action_code == LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY:
            onboarding = SelfStudyConversationalOnboardingService(events=self.events).start(
                workspace_id=workspace.id,
                actor=actor,
                idempotency_key=idempotency_key or f"journey:{journey.id}:begin-goal",
            )
            return {"source_record_id": onboarding.id, "onboarding_id": str(onboarding.id)}

        if action_code == LearningJourneyActionCode.CONTINUE_GOAL_DISCOVERY:
            onboarding = self._onboarding(workspace=workspace, payload=payload, actor=actor)
            changes = payload.get("changes") or {}
            if not changes:
                return {"source_record_id": onboarding.id, "onboarding_id": str(onboarding.id), "no_op": "NO_CHANGES"}
            updated = SelfStudyConversationalOnboardingService(events=self.events).update_context(
                onboarding_id=onboarding.id,
                actor=actor,
                expected_version=int(payload.get("expected_version") or onboarding.version),
                changes=changes,
            )
            return {"source_record_id": updated.id, "onboarding_id": str(updated.id)}

        if action_code in {LearningJourneyActionCode.RESOLVE_CURRICULUM, LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION, LearningJourneyActionCode.RETRY_BLOCKED_STEP}:
            return self._resolve_curriculum_or_resync(journey=journey, workspace=workspace, actor=actor, payload=payload, idempotency_key=idempotency_key)

        if action_code == LearningJourneyActionCode.SELECT_CURRICULUM:
            onboarding = self._onboarding(workspace=workspace, payload=payload, actor=actor)
            selected = SelfStudyConversationalOnboardingService(events=self.events).select_candidate(
                onboarding_id=onboarding.id,
                actor=actor,
                expected_version=int(payload.get("expected_version") or onboarding.version),
                candidate_id=payload.get("candidate_id"),
            )
            return {"source_record_id": selected.selected_resolution_candidate_id, "onboarding_id": str(selected.id)}

        if action_code == LearningJourneyActionCode.CONFIRM_INTENT:
            onboarding = self._onboarding(workspace=workspace, payload=payload, actor=actor)
            completed = SelfStudyConversationalOnboardingService(events=self.events).complete(
                onboarding_id=onboarding.id,
                actor=actor,
                expected_version=int(payload.get("expected_version") or onboarding.version),
            )
            return {"source_record_id": completed.created_intent_id, "onboarding_id": str(completed.id), "intent_id": str(completed.created_intent_id)}

        if action_code == LearningJourneyActionCode.BEGIN_DIAGNOSTIC:
            if not workspace.intent_id:
                raise ValidationError("A confirmed self-study intent is required.", code="SELF_STUDY_INTENT_REQUIRED")
            diagnostic, replayed = CreateEntryDiagnosticService(events=self.events).execute(
                intent_id=workspace.intent_id,
                actor=actor,
                purpose_acknowledged=bool(payload.get("purpose_acknowledged", True)),
            )
            diagnostic = DiagnosticDeliveryService(events=self.events).start(diagnostic.id, actor)
            return {"source_record_id": diagnostic.id, "diagnostic_id": str(diagnostic.id), "replayed": replayed}

        if action_code == LearningJourneyActionCode.CONTINUE_DIAGNOSTIC:
            diagnostic = self._diagnostic(workspace=workspace, payload=payload)
            presentation = DiagnosticDeliveryService(events=self.events).current_item(diagnostic.id, actor)
            return {"source_record_id": diagnostic.id, "diagnostic_id": str(diagnostic.id), "presentation_id": str(presentation.id) if presentation else ""}

        if action_code == LearningJourneyActionCode.CONFIRM_PLACEMENT:
            diagnostic = self._diagnostic(workspace=workspace, payload=payload)
            if diagnostic.status == DiagnosticStatus.READY:
                diagnostic = DiagnosticDeliveryService(events=self.events).start(diagnostic.id, actor)
            profile = FinalizeDiagnosticPlacementService(events=self.events).execute(diagnostic.id)
            return {"source_record_id": profile.id, "diagnostic_id": str(diagnostic.id), "placement_id": str(profile.id)}

        if action_code == LearningJourneyActionCode.PAUSE_JOURNEY:
            paused = LearningJourneyLifecycleService(events=self.events).pause(
                journey_id=journey.id,
                actor=actor,
                expected_version=payload.get("expected_version"),
            )
            return {"source_record_id": paused.id}

        if action_code == LearningJourneyActionCode.RESUME_JOURNEY:
            resumed = LearningJourneyLifecycleService(events=self.events).resume(
                journey_id=journey.id,
                actor=actor,
                expected_version=payload.get("expected_version"),
            )
            return {"source_record_id": resumed.id}

        if action_code == LearningJourneyActionCode.WITHDRAW_JOURNEY:
            if payload.get("confirmation") != "WITHDRAW":
                raise ValidationError("Withdrawal requires explicit confirmation.", code="LEARNING_JOURNEY_WITHDRAWAL_CONFIRMATION_REQUIRED")
            withdrawn = LearningJourneyLifecycleService(events=self.events).withdraw(
                journey_id=journey.id,
                actor=actor,
                expected_version=payload.get("expected_version"),
            )
            return {"source_record_id": withdrawn.id}

        if action_code == LearningJourneyActionCode.SYNCHRONIZE:
            synced = SynchronizeLearningJourneyService(events=self.events).execute(journey_id=journey.id, actor=actor)
            return {"source_record_id": synced.id}

        if action_code == LearningJourneyActionCode.REVISE_INTENT:
            plan = self.invalidation_policy.plan_for(action_code=action_code, payload=payload)
            raise ValidationError(f"Intent revision is not yet executable. {plan.reason}", code="LEARNING_JOURNEY_ACTION_NOT_AVAILABLE")

        raise ValidationError("Journey action is not executable.", code="LEARNING_JOURNEY_ACTION_NOT_AVAILABLE")

    def _resolve_curriculum_or_resync(self, *, journey: LearningJourney, workspace: SelfStudyWorkspace, actor: User, payload: dict, idempotency_key: str) -> dict:
        onboarding = SelfStudyConversationalOnboardingService(events=self.events).get_for_workspace(workspace_id=workspace.id, actor=actor)
        if onboarding and not workspace.intent_id:
            resolved = SelfStudyConversationalOnboardingService(events=self.events).resolve_curriculum(
                onboarding_id=onboarding.id,
                actor=actor,
                expected_version=int(payload.get("expected_version") or onboarding.version),
            )
            return {"source_record_id": resolved.active_resolution_attempt_id, "onboarding_id": str(resolved.id)}
        if workspace.intent_id:
            attempt, replayed = StartCurriculumResolutionService(events=self.events, enqueue=False).execute(
                intent_id=workspace.intent_id,
                actor=actor,
                idempotency_key=idempotency_key or f"journey:{journey.id}:resolve-curriculum:{timezone.now().date().isoformat()}",
            )
            attempt = ResolveCurriculumAttemptService(events=self.events).execute(attempt.id)
            workspace.curriculum_resolution = attempt
            workspace.version += 1
            workspace.save(update_fields=["curriculum_resolution", "version", "updated_at"])
            return {"source_record_id": attempt.id, "resolution_attempt_id": str(attempt.id), "replayed": replayed}
        synced = SynchronizeLearningJourneyService(events=self.events).execute(journey_id=journey.id, actor=actor)
        return {"source_record_id": synced.id, "no_op": "NO_INTENT_OR_ONBOARDING_TO_RESOLVE"}

    def _onboarding(self, *, workspace: SelfStudyWorkspace, payload: dict, actor: User):
        onboarding_id = payload.get("onboarding_id")
        if onboarding_id:
            from apps.self_study.onboarding_models import SelfStudyOnboarding

            return SelfStudyOnboarding.objects.get(id=onboarding_id, workspace=workspace)
        onboarding = SelfStudyConversationalOnboardingService(events=self.events).get_for_workspace(workspace_id=workspace.id, actor=actor)
        if onboarding:
            return onboarding
        return SelfStudyConversationalOnboardingService(events=self.events).start(workspace_id=workspace.id, actor=actor)

    def _diagnostic(self, *, workspace: SelfStudyWorkspace, payload: dict):
        from apps.self_study.diagnostic_models import EntryDiagnostic

        if payload.get("diagnostic_id"):
            return EntryDiagnostic.objects.get(id=payload["diagnostic_id"], intent=workspace.intent)
        if workspace.active_diagnostic_id:
            return workspace.active_diagnostic
        if workspace.intent_id:
            diagnostic = workspace.intent.entry_diagnostics.order_by("-created_at").first()
            if diagnostic:
                return diagnostic
        raise ValidationError("Diagnostic is not available.", code="DIAGNOSTIC_NOT_READY")

    def _response(self, *, receipt: LearningJourneyActionReceipt, journey_id, actor: User, replayed: bool = False) -> dict:
        operation = receipt.operations.order_by("-started_at").first()
        return {
            "receipt": {
                "id": str(receipt.id),
                "action_code": receipt.action_code,
                "status": receipt.status,
                "failure_code": receipt.failure_code,
                "failure_message": receipt.failure_message,
                "replayed": replayed,
            },
            "journey": GetLearningJourneyService().execute(journey_id=journey_id, actor=actor),
            "operation": {
                "result": receipt.status,
                "receipt_id": str(receipt.id),
                "operation_id": str(operation.id) if operation else "",
                "failure_code": receipt.failure_code,
            },
        }

    def _conflict_response(self, *, receipt: LearningJourneyActionReceipt, journey_id, actor: User, code: str, message: str) -> dict:
        return {
            "receipt": {
                "id": str(receipt.id),
                "action_code": receipt.action_code,
                "status": LearningJourneyActionReceiptStatus.CONFLICT,
                "failure_code": code,
                "failure_message": message,
                "replayed": True,
            },
            "journey": GetLearningJourneyService().execute(journey_id=journey_id, actor=actor),
            "operation": {
                "result": LearningJourneyActionReceiptStatus.CONFLICT,
                "receipt_id": str(receipt.id),
                "failure_code": code,
            },
        }

    def _milestone_event(self, action_code: str) -> str:
        return {
            LearningJourneyActionCode.CONFIRM_INTENT: "learning_journey.intent_confirmed",
            LearningJourneyActionCode.RESOLVE_CURRICULUM: "learning_journey.curriculum_resolution_requested",
            LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION: "learning_journey.curriculum_resolution_requested",
            LearningJourneyActionCode.SELECT_CURRICULUM: "learning_journey.curriculum_selected",
            LearningJourneyActionCode.BEGIN_DIAGNOSTIC: "learning_journey.diagnostic_started",
            LearningJourneyActionCode.CONFIRM_PLACEMENT: "learning_journey.placement_confirmed",
            LearningJourneyActionCode.GENERATE_BRIDGE_PLAN: "learning_journey.bridge_plan_requested",
            LearningJourneyActionCode.GENERATE_LEARNING_PLAN: "learning_journey.learning_plan_created",
            LearningJourneyActionCode.ACTIVATE_LEARNING_PLAN: "learning_journey.learning_plan_activated",
            LearningJourneyActionCode.PREPARE_TEACHING_SESSION: "learning_journey.teaching_prepared",
            LearningJourneyActionCode.BEGIN_TEACHING_SESSION: "learning_journey.teaching_session_started",
        }.get(action_code, "")
