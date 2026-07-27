from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher

from ..curriculum_models import (
    CandidateEligibility,
    CurriculumReference,
    CurriculumResolutionCandidate,
    CurriculumSubjectBinding,
    CurriculumSubjectBindingStatus,
    MatchClassification,
    ResolutionAttemptStatus,
)
from ..domain.policy import resolve_effective_policy
from ..models import EffectiveLearningPolicySnapshot, LearningMode, LearningPolicyRuleSet, RequestedDepth
from ..onboarding_models import (
    SelfStudyOnboarding,
    SelfStudyOnboardingIntent,
    SelfStudyOnboardingStage,
    SelfStudyOnboardingStatus,
)
from ..workspace_models import SelfStudyWorkspace, SelfStudyWorkspaceStatus
from .curriculum_services import (
    ConfirmCurriculumSelectionService,
    ResolveCurriculumAttemptService,
    StartCurriculumResolutionService,
    StartOnboardingCurriculumResolutionService,
)
from .services import (
    ActivateSelfStudyIntentService,
    CreateSelfStudyIntentService,
    MarkSelfStudyIntentReadyService,
    _layer,
)
from .workspace_services import SelfStudyOnboardingService, ensure_workspace_access


def _publish(events: EventPublisher, name: str, onboarding: SelfStudyOnboarding, extra: dict | None = None) -> None:
    payload = {
        "onboarding_id": str(onboarding.id),
        "workspace_id": str(onboarding.workspace_id),
        "tenant_id": str(onboarding.tenant_id),
        "learner_id": str(onboarding.learner_id),
        "status": onboarding.status,
        "stage": onboarding.current_stage,
        "version": onboarding.version,
    }
    payload.update(extra or {})
    events.publish(BusinessEvent.create(name, payload=payload))


def _stage_for(onboarding: SelfStudyOnboarding) -> str:
    if not onboarding.topic_query:
        return SelfStudyOnboardingStage.STUDY_TOPIC
    if not onboarding.study_intent:
        return SelfStudyOnboardingStage.STUDY_INTENT
    if onboarding.study_intent == SelfStudyOnboardingIntent.EXAM and not onboarding.qualification_query:
        return SelfStudyOnboardingStage.QUALIFICATION_CONTEXT
    if not onboarding.selected_resolution_candidate_id:
        return SelfStudyOnboardingStage.CURRICULUM_DISCOVERY
    if onboarding.weekly_study_minutes is None:
        return SelfStudyOnboardingStage.WEEKLY_AVAILABILITY
    return SelfStudyOnboardingStage.SUMMARY


def _intent_defaults(choice: str) -> dict[str, str]:
    if choice == SelfStudyOnboardingIntent.EXAM:
        return {
            "desired_depth": RequestedDepth.EXAM_PREPARATION,
            "target_credential": "Exam preparation",
            "pace_preference": "Structured exam preparation",
        }
    if choice == SelfStudyOnboardingIntent.MASTER_SUBJECT:
        return {
            "desired_depth": RequestedDepth.ACADEMIC,
            "target_credential": "",
            "pace_preference": "Deep mastery-oriented study",
        }
    return {
        "desired_depth": RequestedDepth.GENERAL,
        "target_credential": "",
        "pace_preference": "Guided exploratory learning",
    }


def _candidate_binding(candidate: CurriculumResolutionCandidate, tenant) -> CurriculumSubjectBinding | None:
    return (
        CurriculumSubjectBinding.objects.select_related("subject")
        .filter(
            curriculum_version=candidate.curriculum_version,
            tenant=tenant,
            status=CurriculumSubjectBindingStatus.ACTIVE,
            subject__is_active=True,
            subject__institution=tenant,
        )
        .first()
    )


def _candidate_snapshot(candidate: CurriculumResolutionCandidate, rank: int, tenant) -> dict:
    version = candidate.curriculum_version
    reference = version.curriculum_reference
    authority = reference.authority
    binding = _candidate_binding(candidate, tenant)
    eligibility = (
        candidate.eligibility == CandidateEligibility.ELIGIBLE
        and candidate.match_classification in {MatchClassification.EXACT, MatchClassification.STRONG}
    )
    blocker_codes = [] if binding else ["CURRICULUM_SUBJECT_BINDING_MISSING"]
    if not eligibility:
        blocker_codes.extend(candidate.rejection_reasons or ["CURRICULUM_CANDIDATE_NOT_SELECTABLE"])
    return {
        "candidate_id": str(candidate.id),
        "resolution_attempt_id": str(candidate.attempt_id),
        "curriculum_version_id": str(version.id),
        "title": reference.title,
        "subject": reference.subject_area,
        "authority": authority.name,
        "qualification": reference.qualification_type or version.qualification_type,
        "awarding_body": authority.name,
        "jurisdiction": reference.jurisdiction or version.jurisdiction,
        "level": reference.education_stage or version.education_stage,
        "version_label": version.version_label,
        "status": candidate.eligibility,
        "selectable": eligibility and binding is not None,
        "blocker_codes": blocker_codes,
        "match_explanation": (
            "Matched through the governed curriculum resolver."
            if eligibility and binding
            else "This curriculum is verified, but it is not yet available for self-study."
        ),
        "rank": rank,
    }


def _policy_snapshot_for_onboarding(onboarding: SelfStudyOnboarding) -> EffectiveLearningPolicySnapshot:
    policies = list(
        LearningPolicyRuleSet.objects.filter(is_active=True)
        .filter(
            Q(authority=LearningPolicyRuleSet.Authority.PLATFORM)
            | Q(authority=LearningPolicyRuleSet.Authority.TENANT, tenant=onboarding.tenant)
            | Q(
                authority=LearningPolicyRuleSet.Authority.LEARNER,
                tenant=onboarding.tenant,
                learner=onboarding.learner,
            )
        )
        .order_by("authority", "-version")
    )
    selected = {}
    for policy in policies:
        selected.setdefault(policy.authority, policy)
    platform = selected.get(LearningPolicyRuleSet.Authority.PLATFORM)
    if platform is None:
        raise ValidationError("No platform safety policy is configured.", code="EFFECTIVE_POLICY_INVALID")
    ordered = [platform]
    for authority in (LearningPolicyRuleSet.Authority.TENANT, LearningPolicyRuleSet.Authority.LEARNER):
        if authority in selected:
            ordered.append(selected[authority])
    effective = resolve_effective_policy(*[_layer(item) for item in ordered])
    values = asdict(effective)
    for key in (
        "allowed_provider_ids",
        "allowed_source_categories",
        "allowed_licence_categories",
        "allowed_mime_types",
        "allowed_languages",
    ):
        values[key] = sorted(values[key])
    snapshot = EffectiveLearningPolicySnapshot(
        policy_version=onboarding.version,
        source_policy_ids=[str(item.id) for item in ordered],
        **values,
    )
    snapshot.save()
    return snapshot


@dataclass(frozen=True)
class OnboardingProjection:
    onboarding: SelfStudyOnboarding
    next_action: dict

    def to_dict(self) -> dict:
        return {
            "id": str(self.onboarding.id),
            "workspace_id": str(self.onboarding.workspace_id),
            "status": self.onboarding.status,
            "current_stage": self.onboarding.current_stage,
            "topic_query": self.onboarding.topic_query,
            "study_intent": self.onboarding.study_intent,
            "qualification_query": self.onboarding.qualification_query,
            "jurisdiction_query": self.onboarding.jurisdiction_query,
            "awarding_body_query": self.onboarding.awarding_body_query,
            "level_query": self.onboarding.level_query,
            "target_description": self.onboarding.target_description,
            "target_date": self.onboarding.target_date.isoformat() if self.onboarding.target_date else None,
            "target_date_known": self.onboarding.target_date_known,
            "weekly_study_minutes": self.onboarding.weekly_study_minutes,
            "selected_curriculum": self.onboarding.selected_candidate_snapshot or None,
            "created_intent_id": str(self.onboarding.created_intent_id) if self.onboarding.created_intent_id else None,
            "version": self.onboarding.version,
            "next_action": self.next_action,
        }


class SelfStudyConversationalOnboardingService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def get_for_workspace(self, *, workspace_id, actor) -> SelfStudyOnboarding | None:
        workspace = SelfStudyWorkspace.objects.select_related("intent").get(id=workspace_id)
        ensure_workspace_access(actor, workspace)
        return (
            workspace.onboarding_sessions.select_related(
                "active_resolution_attempt",
                "selected_curriculum_version__curriculum_reference__authority",
                "selected_resolution_candidate__curriculum_version__curriculum_reference__authority",
                "created_intent",
            )
            .order_by("-created_at")
            .first()
        )

    def project(self, *, onboarding: SelfStudyOnboarding) -> dict:
        next_action = SelfStudyOnboardingService().summarize(workspace=onboarding.workspace).next_action
        return OnboardingProjection(onboarding=onboarding, next_action=next_action).to_dict()

    @transaction.atomic
    def start(self, *, workspace_id, actor, idempotency_key: str = "") -> SelfStudyOnboarding:
        workspace = SelfStudyWorkspace.objects.select_for_update().get(id=workspace_id)
        ensure_workspace_access(actor, workspace, mutate=True)
        if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED:
            raise ValidationError("Archived workspaces cannot start onboarding.", code="WORKSPACE_ARCHIVED")
        if idempotency_key:
            existing = SelfStudyOnboarding.objects.filter(workspace=workspace, idempotency_key=idempotency_key).first()
            if existing:
                return existing
        existing = workspace.onboarding_sessions.exclude(
            status__in=[SelfStudyOnboardingStatus.COMPLETED, SelfStudyOnboardingStatus.ABANDONED]
        ).order_by("-created_at").first()
        if existing:
            return existing
        onboarding = SelfStudyOnboarding.objects.create(
            tenant=workspace.tenant,
            learner=workspace.learner,
            workspace=workspace,
            idempotency_key=idempotency_key,
        )
        transaction.on_commit(lambda: _publish(self.events, "self_study.onboarding.started", onboarding))
        return onboarding

    @transaction.atomic
    def update_context(self, *, onboarding_id, actor, expected_version: int, changes: dict) -> SelfStudyOnboarding:
        onboarding = SelfStudyOnboarding.objects.select_for_update().select_related("workspace").get(id=onboarding_id)
        ensure_workspace_access(actor, onboarding.workspace, mutate=True)
        onboarding.require_editable()
        if onboarding.version != expected_version:
            raise ValidationError("Onboarding version is stale.", code="ONBOARDING_VERSION_CONFLICT")
        for field, value in changes.items():
            if hasattr(onboarding, field):
                setattr(onboarding, field, value.strip() if isinstance(value, str) else value)
        onboarding.current_stage = _stage_for(onboarding)
        onboarding.status = SelfStudyOnboardingStatus.COLLECTING_CONTEXT
        onboarding.version += 1
        onboarding.full_clean()
        onboarding.save()
        transaction.on_commit(lambda: _publish(self.events, "self_study.onboarding.context_updated", onboarding))
        return onboarding

    @transaction.atomic
    def resolve_curriculum(self, *, onboarding_id, actor, expected_version: int) -> SelfStudyOnboarding:
        onboarding = SelfStudyOnboarding.objects.select_for_update().select_related("workspace").get(id=onboarding_id)
        ensure_workspace_access(actor, onboarding.workspace, mutate=True)
        onboarding.require_editable()
        if onboarding.version != expected_version:
            raise ValidationError("Onboarding version is stale.", code="ONBOARDING_VERSION_CONFLICT")
        if not onboarding.topic_query or not onboarding.study_intent:
            raise ValidationError("Study topic and intent are required.", code="ONBOARDING_CONTEXT_INCOMPLETE")
        policy_snapshot = _policy_snapshot_for_onboarding(onboarding)
        attempt, _ = StartOnboardingCurriculumResolutionService(events=self.events, enqueue=False).execute(
            onboarding_id=onboarding.id,
            actor=actor,
            policy_snapshot=policy_snapshot,
            idempotency_key=f"onboarding-discovery:{onboarding.id}:{onboarding.version}",
        )
        attempt = ResolveCurriculumAttemptService(events=self.events).execute(attempt.id)
        onboarding.active_resolution_attempt = attempt
        onboarding.status = SelfStudyOnboardingStatus.AWAITING_CURRICULUM_SELECTION
        onboarding.current_stage = SelfStudyOnboardingStage.CURRICULUM_SELECTION
        onboarding.version += 1
        onboarding.save(update_fields=["active_resolution_attempt", "status", "current_stage", "version", "updated_at"])
        transaction.on_commit(
            lambda: _publish(
                self.events,
                "self_study.onboarding.curriculum_resolution_requested",
                onboarding,
                {"attempt_id": str(attempt.id), "attempt_status": attempt.status},
            )
        )
        return onboarding

    def candidates(self, *, onboarding_id, actor) -> list[dict]:
        onboarding = SelfStudyOnboarding.objects.select_related("workspace", "active_resolution_attempt").get(id=onboarding_id)
        ensure_workspace_access(actor, onboarding.workspace)
        if not onboarding.active_resolution_attempt_id:
            return []
        candidates = (
            CurriculumResolutionCandidate.objects.select_related("curriculum_version__curriculum_reference__authority")
            .filter(attempt=onboarding.active_resolution_attempt)
            .exclude(eligibility=CandidateEligibility.INELIGIBLE)
            .order_by("hierarchy_rank", "-total_score", "curriculum_version_id")[:8]
        )
        return [_candidate_snapshot(candidate, rank + 1, onboarding.tenant) for rank, candidate in enumerate(candidates)]

    @transaction.atomic
    def select_candidate(self, *, onboarding_id, actor, expected_version: int, candidate_id) -> SelfStudyOnboarding:
        onboarding = SelfStudyOnboarding.objects.select_for_update().get(id=onboarding_id)
        ensure_workspace_access(actor, onboarding.workspace, mutate=True)
        onboarding.require_editable()
        if onboarding.version != expected_version:
            raise ValidationError("Onboarding version is stale.", code="ONBOARDING_VERSION_CONFLICT")
        if not onboarding.active_resolution_attempt_id:
            raise ValidationError("Resolve curricula before selecting a candidate.", code="CURRICULUM_RESOLUTION_REQUIRED")
        candidates = self.candidates(onboarding_id=onboarding.id, actor=actor)
        selected = next((candidate for candidate in candidates if candidate["candidate_id"] == str(candidate_id)), None)
        if not selected:
            raise ValidationError("Selected curriculum was not offered by this onboarding session.", code="CURRICULUM_CANDIDATE_NOT_SELECTABLE")
        if not selected.get("selectable"):
            raise ValidationError("Selected curriculum is not available for self-study.", code="CURRICULUM_SUBJECT_BINDING_MISSING")
        candidate = CurriculumResolutionCandidate.objects.select_related("curriculum_version").get(
            id=candidate_id,
            attempt_id=onboarding.active_resolution_attempt_id,
        )
        onboarding.selected_resolution_candidate = candidate
        onboarding.selected_curriculum_version = candidate.curriculum_version
        onboarding.selected_candidate_snapshot = selected
        onboarding.current_stage = SelfStudyOnboardingStage.WEEKLY_AVAILABILITY
        onboarding.status = SelfStudyOnboardingStatus.REVIEWING_SUMMARY
        onboarding.version += 1
        onboarding.save()
        transaction.on_commit(
            lambda: _publish(
                self.events,
                "self_study.onboarding.curriculum_selected",
                onboarding,
                {"candidate_id": str(candidate.id), "curriculum_version_id": str(candidate.curriculum_version_id)},
            )
        )
        return onboarding

    @transaction.atomic
    def complete(self, *, onboarding_id, actor, expected_version: int) -> SelfStudyOnboarding:
        onboarding = SelfStudyOnboarding.objects.select_for_update().get(id=onboarding_id)
        ensure_workspace_access(actor, onboarding.workspace, mutate=True)
        onboarding.require_editable()
        if onboarding.version != expected_version:
            raise ValidationError("Onboarding version is stale.", code="ONBOARDING_VERSION_CONFLICT")
        if not onboarding.selected_resolution_candidate_id:
            raise ValidationError("Select a governed curriculum before completing onboarding.", code="CURRICULUM_SELECTION_REQUIRED")
        if onboarding.weekly_study_minutes is None:
            raise ValidationError("Weekly study availability is required.", code="WEEKLY_STUDY_TIME_REQUIRED")
        candidate = CurriculumResolutionCandidate.objects.select_related(
            "curriculum_version__curriculum_reference__authority"
        ).get(id=onboarding.selected_resolution_candidate_id)
        binding = _candidate_binding(candidate, onboarding.tenant)
        if binding is None:
            raise ValidationError("Selected curriculum is not yet available for self-study.", code="CURRICULUM_SUBJECT_BINDING_MISSING")
        subject = binding.subject
        reference: CurriculumReference = candidate.curriculum_version.curriculum_reference
        if candidate.attempt_id != onboarding.active_resolution_attempt_id:
            raise ValidationError("Selected curriculum is stale.", code="CURRICULUM_CANDIDATE_NOT_SELECTABLE")
        if (
            candidate.eligibility != CandidateEligibility.ELIGIBLE
            or candidate.match_classification not in {MatchClassification.EXACT, MatchClassification.STRONG}
        ):
            raise ValidationError("Selected curriculum is not eligible.", code="CURRICULUM_CANDIDATE_NOT_SELECTABLE")
        defaults = _intent_defaults(onboarding.study_intent)
        goal = onboarding.target_description or " ".join(
            item
            for item in [
                onboarding.topic_query,
                onboarding.qualification_query,
                candidate.curriculum_version.qualification_type or reference.qualification_type,
            ]
            if item
        )
        intent = CreateSelfStudyIntentService(events=self.events).execute(
            actor=actor,
            learner=onboarding.learner,
            tenant=onboarding.tenant,
            subject=subject,
            mode=LearningMode.SELF_STUDY,
            goal_statement=goal,
            target_title=onboarding.topic_query,
            target_outcomes=[],
            target_credential=(
                onboarding.qualification_query
                if onboarding.qualification_query.casefold()
                in {
                    candidate.curriculum_version.credential_identifier.casefold(),
                    candidate.curriculum_version.qualification_type.casefold(),
                    reference.credential_identifier.casefold(),
                    reference.qualification_type.casefold(),
                }
                else candidate.curriculum_version.qualification_type or reference.qualification_type or defaults["target_credential"]
            ),
            preferred_curriculum_authority=reference.authority.canonical_key,
            jurisdiction=onboarding.jurisdiction_query or reference.jurisdiction,
            preferred_language=candidate.curriculum_version.language,
            learner_age_band=onboarding.level_query or reference.education_stage,
            accessibility_requirements=[],
            desired_depth=defaults["desired_depth"],
            pace_preference=defaults["pace_preference"],
            time_budget_minutes_per_week=onboarding.weekly_study_minutes,
            target_completion_date=onboarding.target_date,
            policy_acknowledged_at=timezone.now(),
        )
        intent = MarkSelfStudyIntentReadyService(events=self.events).execute(intent_id=intent.id, actor=actor, expected_version=intent.version)
        intent = ActivateSelfStudyIntentService(events=self.events).execute(intent_id=intent.id, actor=actor, expected_version=intent.version)
        attempt, _ = StartCurriculumResolutionService(events=self.events, enqueue=False).execute(
            intent_id=intent.id,
            actor=actor,
            idempotency_key=f"onboarding:{onboarding.id}",
            requested_version_id=candidate.curriculum_version_id,
        )
        attempt = ResolveCurriculumAttemptService(events=self.events).execute(attempt.id)
        confirmable = CurriculumResolutionCandidate.objects.filter(
            attempt=attempt,
            curriculum_version_id=candidate.curriculum_version_id,
            eligibility=CandidateEligibility.ELIGIBLE,
            match_classification__in=[MatchClassification.EXACT, MatchClassification.STRONG],
        ).exists()
        if not confirmable:
            raise ValidationError("Selected curriculum is not eligible.", code="CURRICULUM_CANDIDATE_NOT_SELECTABLE")
        if attempt.status == ResolutionAttemptStatus.AWAITING_APPROVAL:
            ConfirmCurriculumSelectionService(events=self.events).execute(
                attempt_id=attempt.id,
                actor=actor,
                curriculum_version_id=candidate.curriculum_version_id,
                reason="Learner selected this governed curriculum during onboarding.",
            )
        workspace = onboarding.workspace
        workspace.intent = intent
        workspace.curriculum_resolution = attempt
        workspace.status = SelfStudyWorkspaceStatus.MATERIALS_REQUIRED
        workspace.version += 1
        workspace.save(update_fields=["intent", "curriculum_resolution", "status", "version", "updated_at"])
        onboarding.created_intent = intent
        onboarding.status = SelfStudyOnboardingStatus.COMPLETED
        onboarding.current_stage = SelfStudyOnboardingStage.COMPLETED
        onboarding.completed_at = timezone.now()
        onboarding.version += 1
        onboarding.save()
        transaction.on_commit(lambda: _publish(self.events, "self_study.onboarding.completed", onboarding, {"intent_id": str(intent.id)}))
        return onboarding

    @transaction.atomic
    def abandon(self, *, onboarding_id, actor, expected_version: int) -> SelfStudyOnboarding:
        onboarding = SelfStudyOnboarding.objects.select_for_update().select_related("workspace").get(id=onboarding_id)
        ensure_workspace_access(actor, onboarding.workspace, mutate=True)
        if onboarding.version != expected_version:
            raise ValidationError("Onboarding version is stale.", code="ONBOARDING_VERSION_CONFLICT")
        changed = onboarding.abandon(when=timezone.now())
        onboarding.save()
        if changed:
            transaction.on_commit(lambda: _publish(self.events, "self_study.onboarding.abandoned", onboarding))
        return onboarding
