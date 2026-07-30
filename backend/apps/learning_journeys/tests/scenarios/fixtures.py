from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.academic.models import ContentConcept, ContentSection, Curriculum, CurriculumUnit, LearningResource, Subject
from apps.assessments.domain.models import LearningEvidence, LearningEvidenceSourceType, LearningEvidenceType, MasteryDecision, MasteryDecisionValue
from apps.learning_journeys.application.services import CreateLearningJourneyService
from apps.self_study.curriculum_models import (
    CompositeCurriculumProposal,
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionAttempt,
    CurriculumVersion,
)
from apps.self_study.graph_models import ConstructionMethod, CurriculumGraph, CurriculumGraphVersion, CurriculumNode, GraphStatus, GraphVersionStatus, NodeType
from apps.self_study.models import EffectiveLearningPolicySnapshot, SelfStudyIntent
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.models import Institution, InstitutionMembership, InstitutionRole, User


class JourneyScenarioFactory:
    def __init__(self, *, prefix: str = "pi8b6"):
        self.prefix = prefix

    def learner(self, email: str = "learner@example.com") -> User:
        return User.objects.create_user(email=f"{self.prefix}-{email}", password="test")

    def institution(self, *, name: str = "Scenario Institution", institution_type: str = "school") -> Institution:
        slug = f"{self.prefix}-{name.lower().replace(' ', '-')}"
        return Institution.objects.create(name=name, slug=slug[:48], institution_type=institution_type)

    def membership(self, *, user: User, institution: Institution, role=InstitutionRole.STUDENT) -> InstitutionMembership:
        return InstitutionMembership.objects.create(user=user, institution=institution, role=role)

    def subject(self, *, institution: Institution, code: str = "BIO", name: str = "Biology") -> Subject:
        return Subject.objects.create(institution=institution, code=f"{self.prefix}-{code}"[:20], name=name)

    def workspace(self, *, learner: User, institution: Institution, display_name: str = "Biology") -> SelfStudyWorkspace:
        return SelfStudyWorkspace.objects.create(learner=learner, tenant=institution, display_name=display_name)

    def curriculum_reference(self, *, actor: User, institution: Institution | None = None, subject_area: str = "Biology"):
        authority = CurriculumAuthority.objects.create(
            canonical_key=f"{self.prefix}-authority-{subject_area.lower()}",
            name=f"{subject_area} Authority",
            authority_type="NATIONAL_CURRICULUM_BODY",
            verification_status="VERIFIED",
            verified_at=timezone.now(),
            verified_by=actor,
        )
        reference = CurriculumReference.objects.create(
            canonical_key=f"{self.prefix}-{subject_area.lower()}",
            title=f"{subject_area} Reference",
            subject_area=subject_area,
            authority=authority,
            source_classification="NATIONAL_OR_REGIONAL",
            jurisdiction="LS",
            language="en",
            tenant=institution,
        )
        version = CurriculumVersion.objects.create(
            curriculum_reference=reference,
            version_label="2026",
            status="ACTIVE",
            canonical_source_uri=f"https://example.test/{self.prefix}/{subject_area.lower()}",
            content_hash=f"sha256:{self.prefix}-{subject_area.lower()}",
            licence_identifier="official",
            provenance_status="COMPLETE",
            language="en",
            jurisdiction="LS",
            created_by=actor,
        )
        return reference, version

    def content_concept(self, *, institution: Institution, subject: Subject, title: str = "Cell structure") -> ContentConcept:
        curriculum = Curriculum.objects.create(subject=subject, institution=institution, name=subject.name, version="2026")
        unit = CurriculumUnit.objects.create(curriculum=curriculum, title="Unit", sequence_number=1)
        resource = LearningResource.objects.create(
            institution=institution,
            subject=subject,
            curriculum=curriculum,
            curriculum_unit=unit,
            title="Scenario resource",
            status=LearningResource.Status.ACTIVE,
        )
        section = ContentSection.objects.create(learning_resource=resource, title="Scenario section", sequence_number=1)
        return ContentConcept.objects.create(content_section=section, title=title, sequence_number=1)

    def competency(self, *, learner: User, institution: Institution, subject: Subject, curriculum_version: CurriculumVersion, stable_key: str = "competency"):
        snapshot = EffectiveLearningPolicySnapshot.objects.create(
            policy_version=1,
            source_policy_ids=["scenario"],
            allowed_provider_ids=["registry"],
            allowed_source_categories=["OPEN_EDUCATIONAL_RESOURCE"],
            allowed_licence_categories=["official"],
            allowed_mime_types=["application/pdf"],
            allowed_languages=["en"],
            maximum_resource_count=10,
            maximum_single_file_bytes=10_000,
            maximum_total_bytes=100_000,
            maximum_cost=Decimal("0"),
        )
        intent = SelfStudyIntent.objects.create(
            learner=learner,
            tenant=institution,
            subject=subject,
            mode="SELF_STUDY",
            goal_statement="Scenario learning",
            preferred_language="en",
            policy_acknowledged_at=timezone.now(),
            status="ACTIVE",
            effective_policy_snapshot=snapshot,
            created_by=learner,
            version=2,
        )
        attempt = CurriculumResolutionAttempt.objects.create(
            intent=intent,
            intent_version=intent.version,
            policy_snapshot=snapshot,
            requested_by=learner,
            status="SELECTED",
            goal_snapshot=intent.goal_statement,
            preferred_language="en",
            requested_depth="CONCEPT",
            algorithm_version="scenario",
            idempotency_key=f"{self.prefix}-{stable_key}",
        )
        proposal = CompositeCurriculumProposal.objects.create(attempt=attempt)
        graph = CurriculumGraph.objects.create(tenant=institution, intent=intent, composite_proposal=proposal, status=GraphStatus.DRAFT)
        graph_version = CurriculumGraphVersion.objects.create(
            graph=graph,
            version_number=1,
            status=GraphVersionStatus.DRAFT,
            source_selection_fingerprint=f"{self.prefix}-{stable_key}",
            builder_algorithm_version="scenario",
            validation_algorithm_version="scenario",
            stable_key_algorithm_version="scenario",
            source_language="en",
            construction_method=ConstructionMethod.CURATED_AUTHORING,
            created_by=learner,
        )
        return CurriculumNode.objects.create(
            graph_version=graph_version,
            stable_key=f"{self.prefix}-{stable_key}",
            node_type=NodeType.COMPETENCY,
            title=stable_key.replace("-", " ").title(),
            ordinal=1,
            source_curriculum_version=curriculum_version,
            authority_namespace="scenario.fixture",
        )

    def mastery_decision(self, *, learner: User, concept: ContentConcept, decision=MasteryDecisionValue.MASTERED):
        evidence_type = LearningEvidenceType.CORRECT_RESPONSE if decision == MasteryDecisionValue.MASTERED else LearningEvidenceType.PARTIAL_UNDERSTANDING
        evidence = LearningEvidence.objects.create(
            learner=learner,
            content_concept=concept,
            source_type=LearningEvidenceSourceType.ASSESSMENT_RESULT,
            source_id=f"{self.prefix}-result",
            evidence_type=evidence_type,
            score=1.0 if decision == MasteryDecisionValue.MASTERED else 0.4,
            confidence=0.9,
            metadata={"scenario": self.prefix},
        )
        mastery = MasteryDecision.objects.create(
            learner=learner,
            content_concept=concept,
            decision=decision,
            confidence=evidence.confidence,
            evidence_count=1,
            rationale="Scenario mastery decision.",
            metadata={"evidence_ids": [str(evidence.id)]},
        )
        return evidence, mastery

    def self_study_journey(self):
        learner = self.learner()
        institution = self.institution(name="Self Study Tenant", institution_type="individual")
        self.membership(user=learner, institution=institution)
        workspace = self.workspace(learner=learner, institution=institution)
        journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=workspace.id, actor=learner)
        return learner, institution, workspace, journey

    def institutional_journey(self):
        admin = self.learner("admin@example.com")
        learner = self.learner("institutional-learner@example.com")
        institution = self.institution(name="Institutional Tenant")
        self.membership(user=admin, institution=institution, role=InstitutionRole.ADMINISTRATOR)
        self.membership(user=learner, institution=institution, role=InstitutionRole.STUDENT)
        subject = self.subject(institution=institution)
        reference, version = self.curriculum_reference(actor=admin, institution=institution)
        competency = self.competency(learner=learner, institution=institution, subject=subject, curriculum_version=version)
        journey = CreateLearningJourneyService().for_institutional_membership(
            learner_id=learner.id,
            institution_id=institution.id,
            actor=admin,
            subject_id=subject.id,
            curriculum_reference_id=reference.id,
            required_competency_ids=[competency.id],
        )
        return admin, learner, institution, subject, reference, competency, journey
