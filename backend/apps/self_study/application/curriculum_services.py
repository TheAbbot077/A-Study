from __future__ import annotations

import hashlib
import json
from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher

from ..curriculum_models import (
    CandidateEligibility,
    CompositeComponentRole,
    CompositeCurriculumComponent,
    CompositeCurriculumProposal,
    CompositeStatus,
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionAttempt,
    CurriculumResolutionCandidate,
    CurriculumSelectionDecision,
    CurriculumVersion,
    CurriculumVersionStatus,
    MatchClassification,
    RegistryStatus,
    ResolutionAttemptStatus,
    SelectionDecisionType,
    VerificationStatus,
)
from ..domain.curriculum_resolution import (
    CandidateFacts,
    POLICY_SOURCE_NAMES,
    RESOLVER_ALGORITHM_VERSION,
    ResolutionInput,
    evaluate_candidate,
)
from ..models import CurriculumResolutionFailure, IntentStatus, LearningMode, SelfStudyIntent
from .services import _has_institutional_authority, ensure_access


def _event(events, name, payload):
    events.publish(BusinessEvent.create(name, payload=payload))


def ensure_registry_governance(actor, tenant_id=None):
    if actor.is_superuser:
        return
    if tenant_id and _has_institutional_authority(actor, tenant_id):
        return
    raise PermissionDenied("CURRICULUM_REGISTRY_ACCESS_DENIED")


class CurriculumRegistryService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def create_authority(self, *, actor, **values):
        tenant = values.get("tenant")
        ensure_registry_governance(actor, tenant.id if tenant else None)
        authority = CurriculumAuthority(**values)
        authority.full_clean()
        authority.save()
        transaction.on_commit(lambda: _event(self.events, "curriculum.authority_created", {"authority_id": str(authority.id)}))
        return authority

    @transaction.atomic
    def verify_authority(self, authority_id, actor):
        authority = CurriculumAuthority.objects.select_for_update().get(id=authority_id)
        ensure_registry_governance(actor, authority.tenant_id)
        authority.verify(actor)
        authority.save(update_fields=["verification_status", "verified_at", "verified_by", "updated_at"])
        transaction.on_commit(lambda: _event(self.events, "curriculum.authority_verified", {"authority_id": str(authority.id)}))
        return authority

    @transaction.atomic
    def suspend_authority(self, authority_id, actor):
        authority = CurriculumAuthority.objects.select_for_update().get(id=authority_id)
        ensure_registry_governance(actor, authority.tenant_id)
        authority.suspend()
        authority.save(update_fields=["status", "verification_status", "updated_at"])
        transaction.on_commit(lambda: _event(self.events, "curriculum.authority_suspended", {"authority_id": str(authority.id)}))
        return authority

    @transaction.atomic
    def create_reference(self, *, actor, **values):
        authority = values["authority"]
        tenant = values.get("tenant")
        tenant_id = tenant.id if tenant else authority.tenant_id
        ensure_registry_governance(actor, tenant_id)
        if authority.tenant_id and authority.tenant_id != tenant_id:
            raise PermissionDenied("CURRICULUM_REGISTRY_ACCESS_DENIED")
        reference = CurriculumReference(**values)
        reference.full_clean()
        reference.save()
        transaction.on_commit(lambda: _event(self.events, "curriculum.reference_created", {"curriculum_id": str(reference.id)}))
        return reference

    @transaction.atomic
    def create_version(self, *, reference_id, actor, **values):
        reference = CurriculumReference.objects.select_for_update().get(id=reference_id)
        ensure_registry_governance(actor, reference.tenant_id or reference.authority.tenant_id)
        version = CurriculumVersion(curriculum_reference=reference, created_by=actor, **values)
        version.save()
        transaction.on_commit(lambda: _event(self.events, "curriculum.version_created", {"version_id": str(version.id)}))
        return version

    @transaction.atomic
    def activate_version(self, version_id, actor):
        version = CurriculumVersion.objects.select_for_update().get(id=version_id)
        reference = CurriculumReference.objects.select_for_update().get(id=version.curriculum_reference_id)
        ensure_registry_governance(actor, reference.tenant_id or reference.authority.tenant_id)
        prior = None
        if reference.current_version_id and reference.current_version_id != version.id:
            prior = CurriculumVersion.objects.select_for_update().get(id=reference.current_version_id)
            version.supersedes = prior
        version.activate()
        version.save(update_fields=["status", "supersedes"])
        if prior:
            prior.status = CurriculumVersionStatus.SUPERSEDED
            prior.save(update_fields=["status"])
        reference.current_version = version
        reference.version += 1
        reference.save(update_fields=["current_version", "version", "updated_at"])
        transaction.on_commit(lambda: _event(self.events, "curriculum.version_activated", {"version_id": str(version.id)}))
        return version

    @transaction.atomic
    def suspend_version(self, version_id, actor):
        version = CurriculumVersion.objects.select_for_update().get(id=version_id)
        ensure_registry_governance(actor, version.curriculum_reference.tenant_id or version.curriculum_reference.authority.tenant_id)
        version.status = CurriculumVersionStatus.SUSPENDED
        version.save(update_fields=["status"])
        transaction.on_commit(lambda: _event(self.events, "curriculum.version_suspended", {"version_id": str(version.id)}))
        return version

    @transaction.atomic
    def supersede_version(self, version_id, replacement_version_id, actor):
        current = CurriculumVersion.objects.select_for_update().get(id=version_id)
        replacement = CurriculumVersion.objects.select_for_update().get(id=replacement_version_id)
        if current.curriculum_reference_id != replacement.curriculum_reference_id:
            raise ValidationError("Replacement must belong to the same curriculum.", code="CURRICULUM_NOT_PERMITTED")
        reference = CurriculumReference.objects.select_for_update().get(id=current.curriculum_reference_id)
        ensure_registry_governance(actor, reference.tenant_id or reference.authority.tenant_id)
        if current.status != CurriculumVersionStatus.ACTIVE or reference.current_version_id != current.id:
            raise ValidationError("Only the current active version may be superseded.", code="CURRICULUM_VERSION_NOT_ACTIVE")
        replacement.supersedes = current
        replacement.activate()
        replacement.save(update_fields=["status", "supersedes"])
        current.status = CurriculumVersionStatus.SUPERSEDED
        current.save(update_fields=["status"])
        reference.current_version = replacement
        reference.version += 1
        reference.save(update_fields=["current_version", "version", "updated_at"])
        transaction.on_commit(
            lambda: _event(
                self.events,
                "curriculum.version_superseded",
                {"version_id": str(current.id), "replacement_version_id": str(replacement.id)},
            )
        )
        return replacement


class StartCurriculumResolutionService:
    def __init__(self, events=None, enqueue=True):
        self.events = events or EventPublisher()
        self.enqueue = enqueue

    @transaction.atomic
    def execute(self, *, intent_id, actor, idempotency_key, requested_version_id=None):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.status != IntentStatus.ACTIVE:
            raise ValidationError("Intent must be active.", code="SELF_STUDY_INTENT_NOT_ACTIVE")
        if not intent.effective_policy_snapshot_id:
            raise ValidationError("Policy snapshot is required.", code="POLICY_SNAPSHOT_REQUIRED")
        if intent.mode == LearningMode.INSTITUTION_GOVERNED:
            if not _has_institutional_authority(actor, intent.tenant_id):
                raise PermissionDenied("INSTITUTIONAL_SELECTION_NOT_AUTHORIZED")
            if not requested_version_id:
                raise ValidationError("Institutional curriculum selection is required.", code="INSTITUTIONAL_CURRICULUM_REQUIRED")
        key = idempotency_key.strip()
        if not key:
            raise ValidationError("Idempotency key is required.", code="CURRICULUM_RESOLUTION_ALREADY_RUNNING")
        existing = CurriculumResolutionAttempt.objects.filter(
            intent=intent, intent_version=intent.version, algorithm_version=RESOLVER_ALGORITHM_VERSION
        ).first()
        if existing:
            return existing, True
        requested_version = None
        if requested_version_id:
            requested_version = CurriculumVersion.objects.filter(id=requested_version_id).filter(
                Q(curriculum_reference__tenant__isnull=True) | Q(curriculum_reference__tenant=intent.tenant)
            ).first()
            if requested_version is None:
                raise ValidationError("Requested curriculum is not permitted.", code="CURRICULUM_NOT_PERMITTED")
        attempt = CurriculumResolutionAttempt.objects.create(
            intent=intent,
            intent_version=intent.version,
            policy_snapshot_id=intent.effective_policy_snapshot_id,
            requested_by=actor,
            requested_version=requested_version,
            goal_snapshot=intent.goal_statement,
            target_credential=intent.target_credential,
            preferred_authority=intent.preferred_curriculum_authority,
            jurisdiction=intent.jurisdiction,
            preferred_language=intent.preferred_language,
            requested_depth=intent.desired_depth,
            education_context=intent.learner_age_band,
            algorithm_version=RESOLVER_ALGORITHM_VERSION,
            idempotency_key=key,
        )

        def after_commit():
            _event(
                self.events,
                "curriculum.resolution_started",
                {"attempt_id": str(attempt.id), "intent_id": str(intent.id), "intent_version": intent.version},
            )
            if self.enqueue:
                from ..infrastructure.celery.tasks import resolve_curriculum_task

                resolve_curriculum_task.delay(str(attempt.id))

        transaction.on_commit(after_commit)
        return attempt, False


def _registry_fingerprint(versions):
    state = [
        {
            "version_id": str(item.id),
            "status": item.status,
            "authority": item.curriculum_reference.authority.verification_status,
        }
        for item in versions
    ]
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


class ResolveCurriculumAttemptService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, attempt_id):
        attempt = CurriculumResolutionAttempt.objects.select_for_update().get(id=attempt_id)
        if attempt.status in {
            ResolutionAttemptStatus.SELECTED,
            ResolutionAttemptStatus.AWAITING_APPROVAL,
            ResolutionAttemptStatus.FAILED,
            ResolutionAttemptStatus.CANCELLED,
            ResolutionAttemptStatus.SUPERSEDED,
        }:
            return attempt
        attempt.status = ResolutionAttemptStatus.EVALUATING
        attempt.started_at = attempt.started_at or timezone.now()
        attempt.save(update_fields=["status", "started_at"])
        intent = SelfStudyIntent.objects.get(id=attempt.intent_id)
        snapshot = attempt.policy_snapshot
        versions = list(
            CurriculumVersion.objects.select_related("curriculum_reference__authority")
            .filter(Q(curriculum_reference__tenant__isnull=True) | Q(curriculum_reference__tenant=intent.tenant))
            .order_by("id")
        )
        fingerprint = _registry_fingerprint(versions)
        attempt.registry_snapshot_identifier = fingerprint
        request = ResolutionInput(
            goal=attempt.goal_snapshot,
            subject_area=intent.subject.name,
            target_credential=attempt.target_credential,
            preferred_authority=attempt.preferred_authority,
            jurisdiction=attempt.jurisdiction,
            preferred_language=attempt.preferred_language,
            education_context=attempt.education_context,
            permitted_sources=tuple(snapshot.curriculum_source_precedence),
            permitted_licences=tuple(snapshot.allowed_licence_categories),
            tenant_id=str(intent.tenant_id),
            today=date.today(),
        )
        evaluated = []
        for version in versions:
            reference, authority = version.curriculum_reference, version.curriculum_reference.authority
            result = evaluate_candidate(
                request,
                CandidateFacts(
                    source_classification=reference.source_classification,
                    subject_area=reference.subject_area,
                    title=reference.title,
                    outcomes=version.target_outcomes_summary,
                    credential_identifier=version.credential_identifier,
                    qualification_type=version.qualification_type,
                    jurisdiction=version.jurisdiction or reference.jurisdiction,
                    education_stage=version.education_stage or reference.education_stage,
                    language=version.language,
                    official_translation_languages=tuple(version.official_translation_languages),
                    generated_translation_permitted=version.generated_translation_permitted,
                    authority_key=authority.canonical_key,
                    authority_verification=authority.verification_status,
                    authority_status=authority.status,
                    reference_status=reference.status,
                    reference_tenant_id=str(reference.tenant_id or ""),
                    version_status=version.status,
                    provenance_status=version.provenance_status,
                    licence_identifier=version.licence_identifier,
                    effective_from=version.effective_from,
                    effective_until=version.effective_until,
                ),
            )
            candidate = CurriculumResolutionCandidate.objects.create(
                attempt=attempt,
                curriculum_version=version,
                hierarchy_rank=result.hierarchy_rank,
                eligibility=result.eligibility,
                match_classification=result.match_classification,
                language_disposition=result.language_disposition,
                score_components=result.score_components,
                total_score=result.total_score,
                confidence=result.confidence,
                requires_approval=result.requires_approval,
                rejection_reasons=list(result.rejection_reasons),
                version_status_snapshot=version.status,
                authority_verification_snapshot=authority.verification_status,
            )
            evaluated.append(candidate)
        viable = [
            item for item in evaluated
            if item.eligibility == CandidateEligibility.ELIGIBLE
            and item.match_classification in {MatchClassification.EXACT, MatchClassification.STRONG}
        ]
        all_viable = list(viable)
        if attempt.requested_version_id:
            requested_viable = any(
                item.curriculum_version_id == attempt.requested_version_id
                for item in all_viable
            )
            if not requested_viable:
                attempt.status = ResolutionAttemptStatus.AWAITING_APPROVAL
                attempt.save(update_fields=["status", "registry_snapshot_identifier"])
                requested = next(
                    (
                        item for item in evaluated
                        if item.curriculum_version_id == attempt.requested_version_id
                    ),
                    None,
                )
                transaction.on_commit(
                    lambda: _event(
                        self.events,
                        "curriculum.selection_awaiting_approval",
                        {
                            "attempt_id": str(attempt.id),
                            "requested_version_id": str(attempt.requested_version_id),
                            "reason_codes": requested.rejection_reasons if requested else ["CURRICULUM_NOT_PERMITTED"],
                        },
                    )
                )
                return attempt
            viable = [
                item for item in viable
                if item.curriculum_version_id == attempt.requested_version_id
            ]
        viable.sort(
            key=lambda item: (
                item.hierarchy_rank,
                0 if attempt.requested_version_id == item.curriculum_version_id else 1,
                -item.total_score,
                str(item.curriculum_version_id),
            )
        )
        if viable:
            winner = viable[0]
            decision_type = (
                SelectionDecisionType.INSTITUTIONAL_SELECTION
                if intent.mode == LearningMode.INSTITUTION_GOVERNED
                else (
                    SelectionDecisionType.LEARNER_CONFIRMED_SELECTION
                    if attempt.requested_version_id
                    else SelectionDecisionType.AUTOMATIC_SELECTION
                )
            )
            decision = CurriculumSelectionDecision.objects.create(
                attempt=attempt,
                intent=intent,
                curriculum_version=winner.curriculum_version,
                decision_type=decision_type,
                hierarchy_rank=winner.hierarchy_rank,
                match_classification=winner.match_classification,
                language_disposition=winner.language_disposition,
                confidence=winner.confidence,
                score_components=winner.score_components,
                reason_codes=["HIGHEST_VIABLE_HIERARCHY", "DETERMINISTIC_SCORE_TIEBREAK"],
                requires_approval=False,
                approved_at=timezone.now() if decision_type != SelectionDecisionType.AUTOMATIC_SELECTION else None,
                approved_by=attempt.requested_by if decision_type != SelectionDecisionType.AUTOMATIC_SELECTION else None,
                algorithm_version=attempt.algorithm_version,
                registry_snapshot_identifier=fingerprint,
            )
            attempt.status = ResolutionAttemptStatus.SELECTED
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=["status", "completed_at", "registry_snapshot_identifier"])
            transaction.on_commit(
                lambda: _event(
                    self.events,
                    "curriculum.selected",
                    {"attempt_id": str(attempt.id), "decision_id": str(decision.id), "version_id": str(winner.curriculum_version_id)},
                )
            )
            return attempt
        partial = [
            item for item in evaluated
            if item.eligibility == CandidateEligibility.ELIGIBLE
            and item.match_classification == MatchClassification.PARTIAL
        ]
        if attempt.requested_version_id:
            partial = []
        composite_permitted = "GOVERNED_COMPOSITE" in snapshot.curriculum_source_precedence
        if len(partial) >= 2 and composite_permitted:
            partial.sort(key=lambda item: (item.hierarchy_rank, -item.total_score, str(item.curriculum_version_id)))
            proposal = CompositeCurriculumProposal.objects.create(
                attempt=attempt,
                rationale_codes=["NO_ADEQUATE_SINGLE_CURRICULUM", "COMPLEMENTARY_ESTABLISHED_CURRICULA"],
            )
            for index, candidate in enumerate(partial[:3], start=1):
                CompositeCurriculumComponent.objects.create(
                    proposal=proposal,
                    curriculum_version=candidate.curriculum_version,
                    role=CompositeComponentRole.PRIMARY if index == 1 else CompositeComponentRole.SUPPLEMENTARY,
                    priority=index,
                    scope_description="Candidate scope remains separate until PI-6F.3 graph validation.",
                )
            attempt.status = ResolutionAttemptStatus.AWAITING_APPROVAL
            attempt.save(update_fields=["status", "registry_snapshot_identifier"])
            transaction.on_commit(
                lambda: _event(self.events, "curriculum.composite_proposed", {"attempt_id": str(attempt.id), "proposal_id": str(proposal.id)})
            )
            return attempt
        reasons = self._failure_reasons(versions, evaluated, composite_permitted)
        failure = CurriculumResolutionFailure.objects.create(
            intent=intent,
            attempt=attempt,
            policy_snapshot=snapshot,
            reason_codes=reasons,
            algorithm_version=attempt.algorithm_version,
            registry_snapshot_identifier=fingerprint,
            recorded_by=attempt.requested_by,
            completed_at=timezone.now(),
        )
        attempt.status = ResolutionAttemptStatus.FAILED
        attempt.completed_at = failure.completed_at
        attempt.save(update_fields=["status", "completed_at", "registry_snapshot_identifier"])
        transaction.on_commit(
            lambda: _event(
                self.events,
                "curriculum.resolution_failed",
                {"attempt_id": str(attempt.id), "failure_id": str(failure.id), "reason_codes": reasons},
            )
        )
        return attempt

    @staticmethod
    def _failure_reasons(versions, candidates, composite_permitted):
        if not versions:
            return ["NO_CURRICULA_REGISTERED"]
        reasons = (
            ["ALL_CANDIDATES_INELIGIBLE"]
            if all(item.eligibility == CandidateEligibility.INELIGIBLE for item in candidates)
            else []
        )
        rejected = {reason for item in candidates for reason in item.rejection_reasons}
        if "SUBJECT_MISMATCH" in rejected:
            reasons.append("NO_SUBJECT_MATCH")
        if "AUTHORITY_NOT_VERIFIED" in rejected:
            reasons.append("NO_TRUSTED_AUTHORITY")
        if "SOURCE_CLASS_NOT_PERMITTED" in rejected:
            reasons.append("NO_PERMITTED_SOURCE")
        if "LANGUAGE_NOT_SUPPORTED" in rejected:
            reasons.append("NO_LANGUAGE_PATH")
        if "LICENCE_NOT_PERMITTED" in rejected:
            reasons.append("NO_LICENCE_COMPATIBILITY")
        if rejected.intersection({"CURRICULUM_NOT_ACTIVE", "CURRICULUM_SUSPENDED", "CURRICULUM_WITHDRAWN"}):
            reasons.append("NO_ACTIVE_VERSION")
        if any(
            item.eligibility == CandidateEligibility.ELIGIBLE
            and item.match_classification in {MatchClassification.PARTIAL, MatchClassification.WEAK}
            for item in candidates
        ):
            reasons.append("NO_ADEQUATE_OUTCOME_ALIGNMENT")
        if not composite_permitted:
            reasons.append("COMPOSITE_NOT_PERMITTED")
        return reasons or ["CURRICULUM_RESOLUTION_FAILED"]


class CompositeCurriculumDecisionService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, attempt_id, actor, approve):
        attempt = CurriculumResolutionAttempt.objects.select_for_update().get(id=attempt_id)
        intent = SelfStudyIntent.objects.get(id=attempt.intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.mode == LearningMode.INSTITUTION_GOVERNED and not _has_institutional_authority(actor, intent.tenant_id):
            raise PermissionDenied("INSTITUTIONAL_SELECTION_NOT_AUTHORIZED")
        proposal = CompositeCurriculumProposal.objects.select_for_update().get(attempt=attempt)
        if proposal.status != CompositeStatus.PROPOSED:
            return proposal
        proposal.status = CompositeStatus.APPROVED if approve else CompositeStatus.REJECTED
        proposal.approved_at = timezone.now() if approve else None
        proposal.approved_by = actor if approve else None
        proposal.save(update_fields=["status", "approved_at", "approved_by"])
        attempt.status = ResolutionAttemptStatus.SELECTED if approve else ResolutionAttemptStatus.FAILED
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=["status", "completed_at"])
        if not approve:
            CurriculumResolutionFailure.objects.create(
                intent=intent,
                attempt=attempt,
                policy_snapshot=attempt.policy_snapshot,
                reason_codes=["COMPOSITE_REJECTED", "NO_ADEQUATE_OUTCOME_ALIGNMENT"],
                algorithm_version=attempt.algorithm_version,
                registry_snapshot_identifier=attempt.registry_snapshot_identifier,
                recorded_by=actor,
                completed_at=attempt.completed_at,
            )
        event = "curriculum.composite_approved" if approve else "curriculum.composite_rejected"
        transaction.on_commit(lambda: _event(self.events, event, {"attempt_id": str(attempt.id), "proposal_id": str(proposal.id)}))
        return proposal


class ConfirmCurriculumSelectionService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, attempt_id, curriculum_version_id, actor, reason=""):
        attempt = CurriculumResolutionAttempt.objects.select_for_update().get(id=attempt_id)
        intent = SelfStudyIntent.objects.get(id=attempt.intent_id)
        ensure_access(actor, intent, mutate=True)
        if attempt.status != ResolutionAttemptStatus.AWAITING_APPROVAL or hasattr(attempt, "composite_proposal"):
            raise ValidationError("Selection is not awaiting confirmation.", code="CURRICULUM_RESOLUTION_ALREADY_COMPLETED")
        candidate = CurriculumResolutionCandidate.objects.filter(
            attempt=attempt,
            curriculum_version_id=curriculum_version_id,
            eligibility=CandidateEligibility.ELIGIBLE,
            match_classification__in=[MatchClassification.EXACT, MatchClassification.STRONG],
        ).first()
        if candidate is None:
            raise ValidationError("Curriculum version is not eligible.", code="CURRICULUM_NOT_PERMITTED")
        if intent.mode == LearningMode.INSTITUTION_GOVERNED:
            if not _has_institutional_authority(actor, intent.tenant_id):
                raise PermissionDenied("INSTITUTIONAL_SELECTION_NOT_AUTHORIZED")
            if not reason.strip():
                raise ValidationError("Institutional override reason is required.", code="INSTITUTIONAL_SELECTION_NOT_AUTHORIZED")
            decision_type = SelectionDecisionType.INSTITUTIONAL_OVERRIDE
        else:
            decision_type = SelectionDecisionType.LEARNER_CONFIRMED_SELECTION
        decision = CurriculumSelectionDecision.objects.create(
            attempt=attempt,
            intent=intent,
            curriculum_version=candidate.curriculum_version,
            decision_type=decision_type,
            hierarchy_rank=candidate.hierarchy_rank,
            match_classification=candidate.match_classification,
            language_disposition=candidate.language_disposition,
            confidence=candidate.confidence,
            score_components=candidate.score_components,
            reason_codes=["ELIGIBLE_ALTERNATIVE_CONFIRMED"],
            override_reason=reason.strip(),
            requires_approval=False,
            approved_at=timezone.now(),
            approved_by=actor,
            algorithm_version=attempt.algorithm_version,
            registry_snapshot_identifier=attempt.registry_snapshot_identifier,
        )
        attempt.status = ResolutionAttemptStatus.SELECTED
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=["status", "completed_at"])
        transaction.on_commit(
            lambda: _event(
                self.events,
                "curriculum.selected",
                {"attempt_id": str(attempt.id), "decision_id": str(decision.id), "version_id": str(candidate.curriculum_version_id)},
            )
        )
        return decision
