from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.self_study.curriculum_models import CurriculumSubjectBindingStatus
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.domain.models import Institution, InstitutionMembership, InstitutionRole, User

from ..domain.enums import (
    LearningJourneySourceType,
    LearningJourneyStatus,
    LearningJourneyStatusReasonCode,
    LearningJourneySubjectBindingSource,
    LearningJourneySubjectBindingStatus,
    LearningJourneyType,
)
from ..domain.models import (
    LearningJourney,
    LearningJourneyCapabilityReferences,
    LearningJourneySourceBinding,
    LearningJourneySubjectBinding,
)
from .adapters import InstitutionalJourneyAdapter, SelfStudyJourneyAdapter


def _publish(events: EventPublisher, name: str, journey: LearningJourney, extra: dict | None = None):
    payload = {
        "journey_id": str(journey.id),
        "learner_id": str(journey.learner_id),
        "journey_type": journey.journey_type,
        "status": journey.status,
        "version": journey.version,
    }
    if journey.institution_id:
        payload["institution_id"] = str(journey.institution_id)
    payload.update(extra or {})
    events.publish(BusinessEvent.create(name, payload=payload))


def can_read_journey(actor: User, journey: LearningJourney) -> bool:
    if actor.is_superuser or actor.id == journey.learner_id:
        return True
    if journey.institution_id:
        return InstitutionMembership.objects.filter(
            user=actor,
            institution_id=journey.institution_id,
            is_active=True,
            role__in=[
                InstitutionRole.ADMINISTRATOR,
                InstitutionRole.INSTITUTION_OWNER,
                InstitutionRole.SYSTEM_ADMINISTRATOR,
                InstitutionRole.TEACHER,
            ],
        ).exists()
    return False


class CreateLearningJourneyService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def for_self_study_workspace(self, *, workspace_id, actor: User) -> LearningJourney:
        workspace = SelfStudyWorkspace.objects.select_related("learner", "tenant").get(id=workspace_id)
        if actor.id != workspace.learner_id and not actor.is_superuser:
            raise PermissionDenied("LEARNING_JOURNEY_WORKSPACE_PERMISSION_DENIED")
        existing = LearningJourneySourceBinding.objects.select_related("journey").filter(
            source_type=LearningJourneySourceType.SELF_STUDY_WORKSPACE,
            source_id=workspace.id,
        ).first()
        if existing:
            return SynchronizeLearningJourneyService(events=self.events).execute(journey_id=existing.journey_id, actor=actor)
        journey = LearningJourney.objects.create(
            learner=workspace.learner,
            journey_type=LearningJourneyType.SELF_STUDY,
            institution=workspace.tenant,
        )
        LearningJourneySourceBinding.objects.create(
            journey=journey,
            source_type=LearningJourneySourceType.SELF_STUDY_WORKSPACE,
            source_id=workspace.id,
            source_version=workspace.version,
        )
        LearningJourneyCapabilityReferences.objects.create(journey=journey)
        transaction.on_commit(lambda: _publish(self.events, "learning_journey.created", journey))
        return SynchronizeLearningJourneyService(events=self.events).execute(journey_id=journey.id, actor=actor)

    @transaction.atomic
    def for_institutional_membership(self, *, learner_id, institution_id, actor: User) -> LearningJourney:
        institution = Institution.objects.get(id=institution_id, is_active=True)
        if not actor.is_superuser and not InstitutionMembership.objects.filter(
            user=actor,
            institution=institution,
            is_active=True,
            role__in=[
                InstitutionRole.ADMINISTRATOR,
                InstitutionRole.INSTITUTION_OWNER,
                InstitutionRole.SYSTEM_ADMINISTRATOR,
            ],
        ).exists():
            raise PermissionDenied("INSTITUTIONAL_JOURNEY_PERMISSION_DENIED")
        membership = InstitutionMembership.objects.filter(user_id=learner_id, institution=institution, is_active=True).first()
        if not membership:
            raise ValidationError("Institutional journey requires active learner membership.", code="INSTITUTIONAL_MEMBERSHIP_REQUIRED")
        existing = LearningJourneySourceBinding.objects.select_related("journey").filter(
            source_type=LearningJourneySourceType.INSTITUTION_MEMBERSHIP,
            source_id=membership.id,
        ).first()
        if existing:
            return SynchronizeLearningJourneyService(events=self.events).execute(journey_id=existing.journey_id, actor=actor)
        journey = LearningJourney.objects.create(
            learner_id=learner_id,
            journey_type=LearningJourneyType.INSTITUTIONAL,
            institution=institution,
            status=LearningJourneyStatus.SUBJECT_BINDING_REQUIRED,
            status_reason_code=LearningJourneyStatusReasonCode.INSTITUTIONAL_ASSIGNMENT_REQUIRED,
        )
        LearningJourneySourceBinding.objects.create(
            journey=journey,
            source_type=LearningJourneySourceType.INSTITUTION_MEMBERSHIP,
            source_id=membership.id,
        )
        LearningJourneyCapabilityReferences.objects.create(journey=journey)
        transaction.on_commit(lambda: _publish(self.events, "learning_journey.created", journey))
        return SynchronizeLearningJourneyService(events=self.events).execute(journey_id=journey.id, actor=actor)


class SynchronizeLearningJourneyService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, journey_id, actor: User, allow_resume: bool = False) -> LearningJourney:
        journey = LearningJourney.objects.select_for_update().get(id=journey_id)
        if not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        if journey.status == LearningJourneyStatus.PAUSED and not allow_resume:
            journey.last_synchronized_at = timezone.now()
            journey.save(update_fields=["last_synchronized_at", "updated_at"])
            return journey
        binding = journey.source_bindings.first()
        if not binding:
            raise ValidationError("Journey source binding is missing.", code="LEARNING_JOURNEY_SOURCE_REQUIRED")
        projection = self._projection_for(binding)
        previous_status = journey.status
        changed = journey.transition_to(
            projection.status,
            reason_code=projection.status_reason.code,
            reason_message=projection.status_reason.message,
            current_step_code=projection.current_step.code,
            when=timezone.now(),
        )
        journey.last_synchronized_at = timezone.now()
        if changed:
            journey.save()
        else:
            journey.save(update_fields=["last_synchronized_at", "updated_at"])
        refs, _ = LearningJourneyCapabilityReferences.objects.get_or_create(journey=journey)
        if refs.update_from_projection(projection.capability_references):
            refs.save()
        self._sync_subject_binding(journey=journey, projection=projection)
        if changed:
            transaction.on_commit(
                lambda: _publish(
                    self.events,
                    "learning_journey.synchronized",
                    journey,
                    {"previous_status": previous_status, "current_step_code": projection.current_step.code},
                )
            )
            transaction.on_commit(
                lambda: _publish(
                    self.events,
                    "learning_journey.state_changed",
                    journey,
                    {"previous_status": previous_status, "status_reason_code": journey.status_reason_code},
                )
            )
        return journey

    def _projection_for(self, binding: LearningJourneySourceBinding):
        if binding.source_type == LearningJourneySourceType.SELF_STUDY_WORKSPACE:
            workspace = SelfStudyWorkspace.objects.select_related(
                "tenant",
                "learner",
                "intent",
                "curriculum_resolution",
                "active_diagnostic",
                "active_bridge_plan",
                "active_teaching_preparation",
                "active_teaching_session",
            ).get(id=binding.source_id)
            return SelfStudyJourneyAdapter(workspace=workspace).project()
        if binding.source_type == LearningJourneySourceType.INSTITUTION_MEMBERSHIP:
            return InstitutionalJourneyAdapter().project()
        raise ValidationError("Unsupported journey source binding.", code="LEARNING_JOURNEY_SOURCE_UNSUPPORTED")

    def _sync_subject_binding(self, *, journey: LearningJourney, projection) -> None:
        subject = projection.subject or {}
        authority = projection.authority or {}
        subject_id = subject.get("id")
        curriculum_reference_id = authority.get("reference_id")
        if not subject_id:
            return
        active = journey.subject_bindings.filter(status=LearningJourneySubjectBindingStatus.ACTIVE).first()
        if active and str(active.subject_id) == str(subject_id) and str(active.curriculum_reference_id or "") == str(curriculum_reference_id or ""):
            return
        if active:
            active.supersede()
            active.save(update_fields=["status", "superseded_at", "version"])
        LearningJourneySubjectBinding.objects.create(
            journey=journey,
            subject_id=subject_id,
            curriculum_reference_id=curriculum_reference_id or None,
            binding_source=LearningJourneySubjectBindingSource.SELF_STUDY_CURRICULUM_RESOLUTION,
            status=LearningJourneySubjectBindingStatus.ACTIVE,
        )


class LearningJourneyLifecycleService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def pause(self, *, journey_id, actor: User, expected_version: int | None = None) -> LearningJourney:
        return self._manual_transition(
            journey_id=journey_id,
            actor=actor,
            expected_version=expected_version,
            status=LearningJourneyStatus.PAUSED,
            reason_code=LearningJourneyStatusReasonCode.MANUALLY_PAUSED,
            event_name="learning_journey.paused",
        )

    @transaction.atomic
    def resume(self, *, journey_id, actor: User, expected_version: int | None = None) -> LearningJourney:
        journey = LearningJourney.objects.select_for_update().get(id=journey_id)
        if expected_version and journey.version != expected_version:
            raise ValidationError("Journey version is stale.", code="LEARNING_JOURNEY_VERSION_CONFLICT")
        resumed = SynchronizeLearningJourneyService(events=self.events).execute(journey_id=journey.id, actor=actor, allow_resume=True)
        transaction.on_commit(lambda: _publish(self.events, "learning_journey.resumed", resumed))
        return resumed

    @transaction.atomic
    def withdraw(self, *, journey_id, actor: User, expected_version: int | None = None) -> LearningJourney:
        return self._manual_transition(
            journey_id=journey_id,
            actor=actor,
            expected_version=expected_version,
            status=LearningJourneyStatus.WITHDRAWN,
            reason_code=LearningJourneyStatusReasonCode.WITHDRAWN_BY_LEARNER,
            event_name="learning_journey.withdrawn",
        )

    @transaction.atomic
    def archive(self, *, journey_id, actor: User, expected_version: int | None = None) -> LearningJourney:
        return self._manual_transition(
            journey_id=journey_id,
            actor=actor,
            expected_version=expected_version,
            status=LearningJourneyStatus.ARCHIVED,
            reason_code=LearningJourneyStatusReasonCode.ARCHIVED_BY_POLICY,
            event_name="learning_journey.archived",
        )

    def _manual_transition(self, *, journey_id, actor: User, expected_version, status, reason_code, event_name) -> LearningJourney:
        journey = LearningJourney.objects.select_for_update().get(id=journey_id)
        if not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        if expected_version and journey.version != expected_version:
            raise ValidationError("Journey version is stale.", code="LEARNING_JOURNEY_VERSION_CONFLICT")
        changed = journey.transition_to(status, reason_code=reason_code, current_step_code=journey.current_step_code)
        if changed:
            journey.save()
            transaction.on_commit(lambda: _publish(self.events, event_name, journey))
        return journey
