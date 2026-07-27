from __future__ import annotations

from django.utils import timezone

from apps.learning_identity.application.ports import ObservationSourceEnvelope
from apps.learning_identity.domain.enums import (
    EvidenceAuthorityClass,
    EvidenceSourceDomain,
    EvidenceSourceType,
    LearningObservationType,
)


class SelfStudyObservationResolver:
    def resolve(self, *, source_domain: str, source_type: str, source_identifier: str, learner_id, tenant_id) -> ObservationSourceEnvelope:
        if source_domain != EvidenceSourceDomain.SELF_STUDY:
            return self._missing(source_domain, source_type, source_identifier, "SOURCE_DOMAIN_UNSUPPORTED")
        if source_type == EvidenceSourceType.DIAGNOSTIC_ATTEMPT:
            return self._diagnostic(source_domain, source_type, source_identifier, learner_id, tenant_id)
        if source_type == EvidenceSourceType.LEARNING_SESSION:
            return self._teaching_session(source_domain, source_type, source_identifier, learner_id, tenant_id)
        return self._missing(source_domain, source_type, source_identifier, "SOURCE_TYPE_UNSUPPORTED")

    def _diagnostic(self, source_domain, source_type, source_identifier, learner_id, tenant_id):
        from apps.self_study.diagnostic_models import DiagnosticStatus, EntryDiagnostic

        diagnostic = EntryDiagnostic.objects.filter(id=source_identifier).first()
        if not diagnostic:
            return self._missing(source_domain, source_type, source_identifier, "SOURCE_NOT_FOUND")
        if str(diagnostic.tenant_id) != str(tenant_id) or str(diagnostic.learner_id) != str(learner_id):
            return self._missing(source_domain, source_type, source_identifier, "SOURCE_TENANT_MISMATCH")
        if diagnostic.status != DiagnosticStatus.COMPLETED:
            return self._missing(source_domain, source_type, source_identifier, "SOURCE_NOT_COMPLETED")
        return ObservationSourceEnvelope(
            exists=True,
            tenant_id=str(diagnostic.tenant_id),
            learner_id=str(diagnostic.learner_id),
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(diagnostic.id),
            source_revision=str(diagnostic.version),
            occurred_at=diagnostic.completed_at or diagnostic.updated_at or timezone.now(),
            observation_type=LearningObservationType.DIAGNOSTIC_COMPLETED,
            authority_class=EvidenceAuthorityClass.DIAGNOSTIC,
            controlled_payload={"status": "COMPLETED"},
            learner_safe_title="Diagnostic completed",
            learner_safe_summary="Recorded after you completed a diagnostic. This is not a grade or mastery decision.",
        )

    def _teaching_session(self, source_domain, source_type, source_identifier, learner_id, tenant_id):
        from apps.self_study.orchestration_models import SelfStudyTeachingSession, SelfStudyTeachingSessionState

        session = SelfStudyTeachingSession.objects.filter(id=source_identifier).first()
        if not session:
            return self._missing(source_domain, source_type, source_identifier, "SOURCE_NOT_FOUND")
        if str(session.tenant_id) != str(tenant_id) or str(session.learner_id) != str(learner_id):
            return self._missing(source_domain, source_type, source_identifier, "SOURCE_TENANT_MISMATCH")
        if session.state != SelfStudyTeachingSessionState.COMPLETED:
            return self._missing(source_domain, source_type, source_identifier, "SOURCE_NOT_COMPLETED")
        return ObservationSourceEnvelope(
            exists=True,
            tenant_id=str(session.tenant_id),
            learner_id=str(session.learner_id),
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(session.id),
            source_revision=str(session.version),
            occurred_at=session.completed_at or session.updated_at or timezone.now(),
            observation_type=LearningObservationType.LEARNING_SESSION_COMPLETED,
            authority_class=EvidenceAuthorityClass.OBSERVATIONAL,
            controlled_payload={"state": "COMPLETED", "turn_count": session.current_turn_sequence},
            learner_safe_title="Learning session completed",
            learner_safe_summary="Recorded after a governed Abbot learning session ended.",
        )

    def _missing(self, source_domain, source_type, source_identifier, reason_code):
        return ObservationSourceEnvelope(
            exists=False,
            tenant_id=None,
            learner_id=None,
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(source_identifier),
            source_revision="",
            occurred_at=None,
            observation_type="",
            authority_class="",
            reason_code=reason_code,
        )
