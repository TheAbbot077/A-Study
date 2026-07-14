from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.academic.domain.models import ContentConcept, ContentSection
from apps.academic.services.learning_content_service import LearningContentService
from apps.academic.services.learning_resource_service import LearningResourceService
from apps.content_processing.application.document_services import DocumentProcessingError
from apps.content_processing.domain.proposal import (
    AcademicImportProposal, AcademicPopulationJob, PopulationJobStatus, PopulationState, ProposalDecision,
    ProposalDecisionType, ProposalEvidence, ProposalItemType, ProposalReviewState, ProposalValidation,
    ProposedConcept, ProposedSection,
)
from apps.content_processing.domain.structure import HierarchyEvidenceStrength, HierarchyNodeType, SemanticSegmentType, StructuralRole
from apps.content_processing.models import ContentProcessingJob, DocumentHierarchy, DocumentSegmentation
from apps.core.events import BusinessEvent, EventPublisher


PROPOSAL_ENGINE_NAME = "deterministic-academic-proposal-engine"
PROPOSAL_VERSION = "6c4-proposal-1"
PROPOSAL_CONFIGURATION_VERSION = "6c4-policy-1"
POPULATION_VERSION = "6c4-population-1"
ACADEMIC_SCHEMA_VERSION = "academic-schema-1"


@dataclass(frozen=True)
class ProposedConceptData:
    segment: object
    title: str
    normalized_title: str
    supporting_text: str
    explanation: str
    confidence: float


@dataclass(frozen=True)
class ProposedSectionData:
    node: object
    title: str
    normalized_title: str
    parent_reference: str
    confidence: float
    concepts: tuple[ProposedConceptData, ...] = ()


@dataclass(frozen=True)
class ProposalEngineResult:
    sections: tuple[ProposedSectionData, ...]
    warnings: tuple[dict[str, object], ...]
    confidence: float
    checksum: str


class DeterministicAcademicProposalEngine:
    name = PROPOSAL_ENGINE_NAME
    version = PROPOSAL_VERSION
    configuration_version = PROPOSAL_CONFIGURATION_VERSION
    _ineligible_types = {SemanticSegmentType.REFERENCE, SemanticSegmentType.FIGURE, SemanticSegmentType.UNKNOWN}
    _synthetic = re.compile(r"^(?:source group \d+|imported content|document content|untitled section|concept\s*\d+available)$", re.I)

    def supports(self, hierarchy, segmentation) -> bool:
        return hierarchy.id == segmentation.document_hierarchy_id

    def generate(self, hierarchy, nodes, segments) -> ProposalEngineResult:
        by_node = {}
        for segment in segments:
            by_node.setdefault(segment.hierarchy_node_id, []).append(segment)
        section_data = []
        seen_sections = set()
        for node in nodes:
            node_segments = by_node.get(node.id, [])
            if node.structural_role not in {StructuralRole.BODY, StructuralRole.APPENDIX} or not node_segments:
                continue
            title = (node.title or "").strip()
            if not title or self._synthetic.match(title):
                title = self._title_from_segment(node_segments[0])
            normalized = self._normalize(title)
            if not normalized or normalized in seen_sections:
                continue
            seen_sections.add(normalized)
            concepts = []
            seen_concepts = set()
            for segment in node_segments:
                concept = self._concept_for(segment, title)
                if concept and concept.normalized_title not in seen_concepts:
                    seen_concepts.add(concept.normalized_title)
                    concepts.append(concept)
            section_data.append(ProposedSectionData(node, title[:255], normalized[:255], str(node.parent_node_id or ""), node.confidence, tuple(concepts)))
        warnings = []
        if not section_data:
            warnings.append({"code": "no_eligible_sections", "message": "No academic sections met the proposal evidence policy."})
        concept_count = sum(len(section.concepts) for section in section_data)
        if not concept_count:
            warnings.append({"code": "no_eligible_concepts", "message": "No concepts met the semantic evidence policy."})
        canonical = [{"title": section.normalized_title, "node": str(section.node.id), "concepts": [concept.normalized_title for concept in section.concepts]} for section in section_data]
        checksum = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
        confidences = [section.confidence for section in section_data] + [concept.confidence for section in section_data for concept in section.concepts]
        confidence = sum(confidences) / len(confidences) if confidences else 0
        return ProposalEngineResult(tuple(section_data), tuple(warnings), confidence, checksum)

    def _concept_for(self, segment, section_title: str) -> ProposedConceptData | None:
        text = (segment.normalized_text or "").strip()
        if segment.segment_type in self._ineligible_types or len(text) < 40 or segment.confidence < .55:
            return None
        title = self._concept_title(text, section_title, segment.segment_type)
        normalized = self._normalize(title)
        if not normalized or self._synthetic.match(title) or re.fullmatch(r"(?:19|20)\d{2}", title):
            return None
        return ProposedConceptData(segment, title[:255], normalized[:255], text, f"Proposed from a {segment.segment_type.replace('_', ' ')} semantic segment with source-block and page provenance.", min(segment.confidence, .95))

    def _title_from_segment(self, segment) -> str:
        return self._concept_title(segment.normalized_text or "", "Source material", segment.segment_type)

    def _concept_title(self, text: str, section_title: str, segment_type: str) -> str:
        first = re.split(r"[.!?\n:]", text.strip(), maxsplit=1)[0].strip()
        words = first.split()
        if 2 <= len(words) <= 10 and len(first) <= 100:
            return first
        label = segment_type.replace("_", " ").title()
        return f"{section_title}: {label}"[:255]

    def _normalize(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


class ValidateAcademicProposalService:
    def validate(self, result: ProposalEngineResult) -> list[dict[str, object]]:
        findings = []
        section_titles = [section.normalized_title for section in result.sections]
        if len(section_titles) != len(set(section_titles)):
            findings.append({"code": "duplicate_sections", "passed": False, "severity": "error", "message": "Duplicate proposed sections were detected."})
        for section in result.sections:
            concept_titles = [concept.normalized_title for concept in section.concepts]
            if len(concept_titles) != len(set(concept_titles)):
                findings.append({"code": "duplicate_concepts", "passed": False, "severity": "error", "message": "Duplicate concepts were detected within a proposed section."})
            for concept in section.concepts:
                if not concept.supporting_text.strip() or concept.segment is None:
                    findings.append({"code": "missing_concept_evidence", "passed": False, "severity": "error", "message": "A proposed concept lacks semantic evidence."})
        findings.append({"code": "proposal_consistency", "passed": not any(not finding["passed"] for finding in findings), "severity": "info", "message": "Proposal consistency validation completed."})
        return findings


class GenerateAcademicImportProposalService:
    def __init__(self, engine=None, validator=None, event_publisher=None) -> None:
        self.engine = engine or DeterministicAcademicProposalEngine()
        self.validator = validator or ValidateAcademicProposalService()
        self.event_publisher = event_publisher or EventPublisher()

    def execute(self, context):
        hierarchy = DocumentHierarchy.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id).order_by("-created_at").first()
        segmentation = DocumentSegmentation.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id).order_by("-created_at").first()
        if not hierarchy or not segmentation or not self.engine.supports(hierarchy, segmentation):
            raise DocumentProcessingError("Hierarchy and segmentation evidence are required.", "proposal_generation_failed")
        existing = AcademicImportProposal.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id, document_hierarchy=hierarchy, document_segmentation=segmentation, proposal_version=self.engine.version, pipeline_version=context.pipeline_version).first()
        if existing:
            return existing, list(existing.warnings)
        nodes = list(hierarchy.nodes.select_related("parent_node").order_by("ordinal"))
        segments = list(segmentation.segments.order_by("ordinal"))
        result = self.engine.generate(hierarchy, nodes, segments)
        findings = self.validator.validate(result)
        failed = [finding for finding in findings if not finding["passed"]]
        if failed:
            raise DocumentProcessingError("The academic proposal failed deterministic validation.", "section_validation_failed")
        review_required = bool(result.warnings) or hierarchy.review_recommended or result.confidence < .7
        with transaction.atomic():
            proposal = AcademicImportProposal.objects.create(job_id=context.job_id, attempt_id=context.attempt_id, resource_id=context.resource_id, document_hierarchy=hierarchy, document_segmentation=segmentation, pipeline_version=context.pipeline_version, proposal_engine=self.engine.name, proposal_version=self.engine.version, configuration_version=self.engine.configuration_version, review_state=ProposalReviewState.READY_FOR_REVIEW, confidence=result.confidence, statistics={"section_count": len(result.sections), "concept_count": sum(len(section.concepts) for section in result.sections)}, warnings=list(result.warnings), review_required=review_required, result_checksum=result.checksum)
            for finding in findings:
                ProposalValidation.objects.create(proposal=proposal, code=finding["code"], severity=finding["severity"], passed=finding["passed"], public_message=finding["message"])
            for section_order, data in enumerate(result.sections, start=1):
                section = ProposedSection.objects.create(proposal=proposal, title=data.title, normalized_title=data.normalized_title, parent_reference=data.parent_reference, hierarchy_node=data.node, ordering=section_order, source_page_start=data.node.source_page_start, source_page_end=data.node.source_page_end, confidence=data.confidence, evidence={"hierarchy_evidence_strength": data.node.evidence_strength})
                ProposalEvidence.objects.create(proposal=proposal, item_type=ProposalItemType.SECTION, proposed_section=section, hierarchy_node=data.node, source_page_start=data.node.source_page_start, source_page_end=data.node.source_page_end, evidence_strength=data.node.evidence_strength, confidence=data.confidence, reasoning_metadata={"reason": "eligible_hierarchy_node"})
                for concept_order, concept_data in enumerate(data.concepts, start=1):
                    concept = ProposedConcept.objects.create(proposal=proposal, proposed_section=section, semantic_segment=concept_data.segment, title=concept_data.title, normalized_title=concept_data.normalized_title, supporting_text=concept_data.supporting_text, explanation=concept_data.explanation, ordering=concept_order, source_page_start=concept_data.segment.source_page_start, source_page_end=concept_data.segment.source_page_end, confidence=concept_data.confidence, evidence={"segment_type": concept_data.segment.segment_type})
                    relationships = list(concept_data.segment.block_relationships.select_related("extracted_block").order_by("ordinal"))
                    if not relationships:
                        raise DocumentProcessingError("A proposed concept lacks extracted-block provenance.", "concept_validation_failed")
                    for relationship in relationships:
                        ProposalEvidence.objects.create(proposal=proposal, item_type=ProposalItemType.CONCEPT, proposed_section=section, proposed_concept=concept, hierarchy_node=data.node, semantic_segment=concept_data.segment, extracted_block=relationship.extracted_block, source_page_start=concept_data.segment.source_page_start, source_page_end=concept_data.segment.source_page_end, evidence_strength=concept_data.segment.evidence_strength, confidence=concept_data.confidence, reasoning_metadata={"relationship_role": relationship.relationship_role})
        self.event_publisher.publish(BusinessEvent.create("academic_import.proposal_created", payload={"proposal_id": str(proposal.id), "job_id": context.job_id, **proposal.statistics}))
        if proposal.review_required:
            self.event_publisher.publish(BusinessEvent.create("academic_import.review_required", payload={"proposal_id": str(proposal.id), "job_id": context.job_id}))
        return proposal, list(result.warnings)


class ReviewProposalService:
    def __init__(self, event_publisher=None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def begin(self, proposal, actor=None):
        proposal.begin_review(); proposal.save(update_fields=["review_state"])
        self.event_publisher.publish(BusinessEvent.create("academic_import.review_started", payload={"proposal_id": str(proposal.id), "actor_id": str(actor.id) if actor else None}))
        return proposal


class ApproveProposalService:
    def __init__(self, event_publisher=None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def approve(self, proposal, actor=None, reason="", with_edits=False, compatibility_approval=False):
        proposal.approve(with_edits); proposal.save(update_fields=["review_state", "decision", "population_state"])
        ProposalDecision.objects.create(proposal=proposal, decision=proposal.decision, decided_by=actor, reason=reason, metadata={"compatibility_approval": compatibility_approval})
        self.event_publisher.publish(BusinessEvent.create("academic_import.approved", payload={"proposal_id": str(proposal.id), "decision": proposal.decision, "actor_id": str(actor.id) if actor else None}))
        return proposal


class RejectProposalService:
    def reject(self, proposal, actor=None, reason=""):
        proposal.reject(); proposal.save(update_fields=["review_state", "decision", "population_state"])
        ProposalDecision.objects.create(proposal=proposal, decision=ProposalDecisionType.REJECTED, decided_by=actor, reason=reason)
        EventPublisher().publish(BusinessEvent.create("academic_import.rejected", payload={"proposal_id": str(proposal.id), "actor_id": str(actor.id) if actor else None}))
        return proposal


class SupersedeProposalService:
    def supersede(self, proposal, actor=None, reason=""):
        proposal.supersede(); proposal.save(update_fields=["review_state", "decision", "population_state"])
        ProposalDecision.objects.create(proposal=proposal, decision=ProposalDecisionType.SUPERSEDED, decided_by=actor, reason=reason)
        EventPublisher().publish(BusinessEvent.create("academic_import.superseded", payload={"proposal_id": str(proposal.id), "actor_id": str(actor.id) if actor else None}))
        return proposal


class RetryAcademicPopulationService:
    def retry(self, proposal, actor=None):
        if proposal.review_state not in {ProposalReviewState.APPROVED, ProposalReviewState.APPROVED_WITH_EDITS} or proposal.population_state != PopulationState.POPULATION_FAILED:
            raise DocumentProcessingError("Only a failed population for an approved proposal may be retried.", "population_conflict")
        population = proposal.population_jobs.filter(status=PopulationJobStatus.POPULATION_FAILED).order_by("-created_at").first()
        if population is None:
            raise DocumentProcessingError("The failed population job is missing.", "population_conflict")
        proposal.population_state = PopulationState.READY_FOR_POPULATION
        proposal.save(update_fields=["population_state"])
        population.status = PopulationJobStatus.READY_FOR_POPULATION
        population.failure_code = ""
        population.save(update_fields=["status", "failure_code"])
        EventPublisher().publish(BusinessEvent.create("academic_population.retried", payload={"proposal_id": str(proposal.id), "population_job_id": str(population.id), "actor_id": str(actor.id) if actor else None}))
        return population


class PopulateAcademicPlatformService:
    def __init__(self, learning_content_service=None, learning_resource_service=None, event_publisher=None) -> None:
        self.events = event_publisher or EventPublisher()
        self.content = learning_content_service or LearningContentService(event_publisher=self.events)
        self.resources = learning_resource_service or LearningResourceService(event_publisher=self.events)

    def execute(self, context, proposal=None):
        proposal = proposal or AcademicImportProposal.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id).order_by("-created_at").first()
        if not proposal or proposal.population_state != PopulationState.READY_FOR_POPULATION or proposal.review_state not in {ProposalReviewState.APPROVED, ProposalReviewState.APPROVED_WITH_EDITS}:
            raise DocumentProcessingError("Only an approved proposal ready for population may be published.", "proposal_approval_failed")
        population, created = AcademicPopulationJob.objects.get_or_create(proposal=proposal, population_version=POPULATION_VERSION, academic_schema_version=ACADEMIC_SCHEMA_VERSION, defaults={"job_id": context.job_id, "attempt_id": context.attempt_id})
        if population.status == PopulationJobStatus.POPULATED:
            return population, []
        population.status = PopulationJobStatus.POPULATION_IN_PROGRESS; population.started_at = timezone.now(); population.save(update_fields=["status", "started_at"])
        proposal.population_state = PopulationState.POPULATION_IN_PROGRESS; proposal.save(update_fields=["population_state"])
        self.events.publish(BusinessEvent.create("academic_population.started", payload={"population_job_id": str(population.id), "proposal_id": str(proposal.id)}))
        created_sections = updated_sections = created_concepts = updated_concepts = 0
        try:
            with transaction.atomic():
                for proposed_section in proposal.proposed_sections.order_by("ordering"):
                    section = proposed_section.populated_section
                    if section is None:
                        section = ContentSection.objects.filter(learning_resource=proposal.resource, sequence_number=proposed_section.ordering).first()
                    description = "\n\n".join(concept.supporting_text for concept in proposed_section.proposed_concepts.order_by("ordering"))
                    if section is None:
                        section = self.content.create_section(proposal.resource, proposed_section.title, proposed_section.ordering, description)
                        created_sections += 1
                    else:
                        self.content.update_section(section, title=proposed_section.title, description=description, sequence_number=proposed_section.ordering, is_active=True)
                        updated_sections += 1
                    section.review_status = ContentSection.ReviewStatus.APPROVED
                    section.quality_status = ContentSection.QualityStatus.ACCEPTABLE
                    section.approved_at = timezone.now()
                    section.save(update_fields=["review_status", "quality_status", "approved_at", "updated_at"])
                    proposed_section.populated_section = section; proposed_section.save(update_fields=["populated_section"])
                    for proposed_concept in proposed_section.proposed_concepts.order_by("ordering"):
                        concept = proposed_concept.populated_concept
                        if concept is None:
                            concept = ContentConcept.objects.filter(content_section=section, sequence_number=proposed_concept.ordering).first()
                        if concept is None:
                            concept = self.content.create_concept(section, proposed_concept.title, proposed_concept.ordering, proposed_concept.supporting_text, proposed_concept.explanation)
                            created_concepts += 1
                        else:
                            self.content.update_concept(concept, title=proposed_concept.title, description=proposed_concept.supporting_text, learning_objective=proposed_concept.explanation, sequence_number=proposed_concept.ordering, is_active=True)
                            updated_concepts += 1
                        concept.review_status = ContentConcept.ReviewStatus.APPROVED
                        concept.quality_status = ContentConcept.QualityStatus.ACCEPTABLE
                        concept.approved_at = timezone.now()
                        concept.save(update_fields=["review_status", "quality_status", "approved_at", "updated_at"])
                        proposed_concept.populated_concept = concept; proposed_concept.save(update_fields=["populated_concept"])
                if proposal.resource.status != proposal.resource.Status.ACTIVE:
                    self.resources.activate_resource(proposal.resource)
                statistics = {"created_sections": created_sections, "updated_sections": updated_sections, "created_concepts": created_concepts, "updated_concepts": updated_concepts}
                checksum = hashlib.sha256(json.dumps({"proposal": str(proposal.id), **statistics}, sort_keys=True).encode()).hexdigest()
                population.status = PopulationJobStatus.POPULATED; population.created_sections = created_sections; population.updated_sections = updated_sections; population.created_concepts = created_concepts; population.updated_concepts = updated_concepts; population.statistics = statistics; population.checksum = checksum; population.completed_at = timezone.now(); population.save()
                proposal.population_state = PopulationState.POPULATED; proposal.save(update_fields=["population_state"])
        except Exception as exc:
            failure_code = "population_conflict" if isinstance(exc, IntegrityError) else "population_failed"
            population.status = PopulationJobStatus.POPULATION_FAILED; population.failure_code = failure_code; population.completed_at = timezone.now(); population.save(update_fields=["status", "failure_code", "completed_at"])
            proposal.population_state = PopulationState.POPULATION_FAILED; proposal.save(update_fields=["population_state"])
            self.events.publish(BusinessEvent.create("academic_population.failed", payload={"population_job_id": str(population.id), "proposal_id": str(proposal.id), "failure_code": population.failure_code}))
            raise DocumentProcessingError("Academic population could not be completed safely.", failure_code) from exc
        self.events.publish(BusinessEvent.create("academic_population.completed", payload={"population_job_id": str(population.id), "proposal_id": str(proposal.id), **population.statistics}))
        return population, []
