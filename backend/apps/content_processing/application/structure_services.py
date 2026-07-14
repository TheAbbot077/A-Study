from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from django.db import transaction

from apps.content_processing.application.document_services import DocumentProcessingError
from apps.content_processing.domain.extraction import ExtractedBlockType, EvidenceOrigin
from apps.content_processing.domain.models import JobStatus
from apps.content_processing.domain.structure import (
    BlockDisposition, DocumentHierarchy, DocumentHierarchyNode, DocumentSegmentation, HierarchyBlockClassification,
    HierarchyEvidenceStrength, HierarchyNodeBlock, HierarchyNodeType, NodeBlockRole, SegmentBlockRole,
    SegmentationEvidenceStrength, SemanticSegment, SemanticSegmentBlock, SemanticSegmentType, StructuralRole,
)
from apps.content_processing.models import ContentProcessingJob, DocumentExtraction


RECONSTRUCTOR_NAME = "deterministic-evidence-reconstructor"
RECONSTRUCTOR_VERSION = "6c3-reconstructor-1"
SEGMENTER_NAME = "deterministic-semantic-segmenter"
SEGMENTER_VERSION = "6c3-segmenter-1"
STRUCTURE_CONFIGURATION_VERSION = "6c3-policy-1"


class StructurePolicy:
    maximum_nodes = 5_000
    maximum_depth = 8
    maximum_unresolved_blocks = 1_000
    fallback_blocks_per_group = 20
    repeated_noise_ratio = .6
    maximum_diagnostics = 100


class SegmentationPolicy:
    minimum_meaningful_characters = 40
    preferred_characters = 2_500
    maximum_characters = 6_000
    maximum_blocks_per_segment = 40
    maximum_segments = 20_000


@dataclass(frozen=True)
class HeadingCandidate:
    block: object
    candidate_title: str
    candidate_level: int
    confidence: float
    evidence_strength: str
    numbering_pattern: str = ""
    rejection_reasons: tuple[str, ...] = ()


@dataclass
class NodeCandidate:
    key: str
    parent_key: str | None
    node_type: str
    role: str
    title: str
    depth: int
    ordinal: int
    start: int
    end: int
    block_ids: list[str] = field(default_factory=list)
    heading_block_id: str | None = None
    confidence: float = .7
    strength: str = HierarchyEvidenceStrength.HEURISTICALLY_INFERRED
    evidence: dict[str, object] = field(default_factory=dict)


def _page(block) -> int | None:
    value = (block.page_reference or {}).get("page_number")
    return int(value) if value is not None else None


class DocumentStyleAnalyzer:
    def analyze(self, blocks) -> dict[str, object]:
        sizes = [float((block.typography or {}).get("font_size", 0)) for block in blocks if (block.typography or {}).get("font_size")]
        rounded = [round(value, 1) for value in sizes]
        dominant = Counter(rounded).most_common(1)[0][0] if rounded else None
        heading_sizes = sorted({value for value in rounded if dominant and value > dominant * 1.08}, reverse=True)
        styles = Counter(str((block.structural_hints or {}).get("style_name", "")).lower() for block in blocks)
        return {"dominant_body_font_size": dominant, "heading_font_sizes": heading_sizes, "style_frequencies": dict(styles)}


class HeadingPolicy:
    _numbered = re.compile(r"^(?:(chapter|part|section|appendix)\s+)?([A-Z]|[IVXLCDM]+|\d+(?:\.\d+){0,7})\b", re.I)
    _date = re.compile(r"^(?:\d{1,2}[-/.]){2}\d{2,4}$|^(?:19|20)\d{2}$")
    _url = re.compile(r"^(?:https?://|www\.)|@|\.(?:pdf|docx?)$", re.I)
    _synthetic = re.compile(r"^(?:imported content|document content|untitled section|section\s+\d+|concept\s*\d+available)$", re.I)

    def candidates(self, blocks, style_profile, classifications) -> list[HeadingCandidate]:
        candidates: list[HeadingCandidate] = []
        dominant = style_profile.get("dominant_body_font_size") or 0
        sizes = style_profile.get("heading_font_sizes") or []
        for index, block in enumerate(blocks):
            text = (block.normalized_text or "").strip()
            if not text or classifications[str(block.id)]["disposition"] == BlockDisposition.EXCLUDED:
                continue
            reasons = self.rejection_reasons(block, text)
            explicit_level = {ExtractedBlockType.HEADING_1: 1, ExtractedBlockType.HEADING_2: 2, ExtractedBlockType.HEADING_3: 3}.get(block.block_type)
            style_name = str((block.structural_hints or {}).get("style_name", "")).lower()
            style_match = re.search(r"heading\s*([1-9])", style_name)
            font_size = float((block.typography or {}).get("font_size", 0) or 0)
            size_level = sizes.index(round(font_size, 1)) + 1 if round(font_size, 1) in sizes else None
            number = self._numbered.match(text)
            numbering = number.group(2) if number else ""
            number_level = numbering.count(".") + 1 if numbering and numbering[0].isdigit() else 1
            has_body_after = index + 1 < len(blocks) and bool((blocks[index + 1].normalized_text or "").strip())
            evidence_count = sum(bool(item) for item in (explicit_level, style_match, size_level, number and len(text) <= 160, (block.typography or {}).get("bold") and len(text.split()) <= 14))
            if reasons or not has_body_after or evidence_count < 1:
                continue
            level = explicit_level or (int(style_match.group(1)) if style_match else None) or number_level or size_level or 1
            level = min(level, StructurePolicy.maximum_depth)
            confidence = min(.98, .55 + evidence_count * .12)
            strength = HierarchyEvidenceStrength.SOURCE_EXPLICIT if explicit_level or style_match else HierarchyEvidenceStrength.STRONGLY_INFERRED if evidence_count >= 2 else HierarchyEvidenceStrength.HEURISTICALLY_INFERRED
            candidates.append(HeadingCandidate(block, text[:512], level, confidence, strength, numbering))
        return candidates

    def rejection_reasons(self, block, text: str) -> tuple[str, ...]:
        reasons = []
        if self._date.match(text): reasons.append("date_like")
        if self._url.search(text): reasons.append("url_email_or_filename")
        if self._synthetic.match(re.sub(r"\s+", " ", text)): reasons.append("synthetic_placeholder")
        if block.block_type in {ExtractedBlockType.PAGE_NUMBER, ExtractedBlockType.HEADER, ExtractedBlockType.FOOTER, ExtractedBlockType.TABLE_CELL, ExtractedBlockType.TOC_ENTRY}: reasons.append("ineligible_block_type")
        if len(text) > 180 or text.endswith((".", ";", ",")): reasons.append("prose_like")
        if block.evidence_origin == EvidenceOrigin.OCR_INFERRED and block.confidence < .55: reasons.append("weak_ocr")
        return tuple(reasons)


class DeterministicHierarchyReconstructor:
    def __init__(self) -> None:
        self.style_analyzer = DocumentStyleAnalyzer()
        self.heading_policy = HeadingPolicy()

    def reconstruct(self, blocks):
        blocks = list(blocks)
        style_profile = self.style_analyzer.analyze(blocks)
        classifications = self._classify_blocks(blocks)
        headings = self.heading_policy.candidates(blocks, style_profile, classifications)
        nodes = self._build_nodes(blocks, headings, classifications)
        warnings = []
        if not headings:
            warnings.append({"code": "fallback_hierarchy_generated", "message": "No trustworthy heading hierarchy was found; conservative source groups were generated."})
        if any(value["disposition"] == BlockDisposition.REVIEW_REQUIRED for value in classifications.values()):
            warnings.append({"code": "uncertain_noise_classification", "message": "Some possible noise remains available for review."})
        toc_titles = [re.sub(r"\.{3,}.*$", "", (block.normalized_text or "")).strip().lower() for block in blocks if classifications[str(block.id)]["role"] == StructuralRole.TABLE_OF_CONTENTS and (block.normalized_text or "").strip()]
        body_titles = [candidate.candidate_title.strip().lower() for candidate in headings]
        if toc_titles and body_titles and not any(title in body_titles for title in toc_titles if title not in {"contents", "table of contents"}):
            warnings.append({"code": "toc_body_mismatch", "message": "Table-of-contents evidence did not match reconstructed body headings."})
        return nodes, classifications, style_profile, warnings

    def _classify_blocks(self, blocks):
        page_count = max(1, len({_page(block) for block in blocks if _page(block)}))
        occurrences: dict[str, set[int]] = defaultdict(set)
        for block in blocks:
            text = re.sub(r"\s+", " ", (block.normalized_text or "").strip().lower())
            if text and _page(block): occurrences[text].add(_page(block))
        result = {}
        for block in blocks:
            text = re.sub(r"\s+", " ", (block.normalized_text or "").strip().lower())
            role, disposition, reason, confidence = StructuralRole.BODY, BlockDisposition.INCLUDED, "body_evidence", .85
            if block.block_type == ExtractedBlockType.PAGE_NUMBER:
                role, disposition, reason, confidence = StructuralRole.PROBABLE_NOISE, BlockDisposition.EXCLUDED, "numeric_margin_pattern", .98
            elif block.block_type in {ExtractedBlockType.HEADER, ExtractedBlockType.FOOTER} or (
                text
                and page_count > 1
                and len(occurrences[text]) > 1
                and len(occurrences[text]) / page_count >= StructurePolicy.repeated_noise_ratio
                and len(text) < 160
            ):
                role, disposition, reason, confidence = StructuralRole.PROBABLE_NOISE, BlockDisposition.EXCLUDED, "repeated_margin_text", .92
            elif text in {"contents", "table of contents"} or block.block_type == ExtractedBlockType.TOC_ENTRY:
                role, disposition, reason, confidence = StructuralRole.TABLE_OF_CONTENTS, BlockDisposition.EXCLUDED, "toc_navigation", .95
            elif re.search(r"\.{3,}\s*(?:\d+|[ivxlcdm]+)\s*$", text, re.I):
                role, disposition, reason, confidence = StructuralRole.TABLE_OF_CONTENTS, BlockDisposition.EXCLUDED, "toc_dotted_leader", .9
            elif text.startswith(("copyright", "all rights reserved")):
                role, disposition, reason, confidence = StructuralRole.COPYRIGHT, BlockDisposition.EXCLUDED, "copyright_notice", .95
            elif text in {"preface", "foreword", "dedication", "acknowledgements", "acknowledgments"}:
                role, disposition, reason, confidence = getattr(StructuralRole, text.upper() if text != "acknowledgments" else "ACKNOWLEDGEMENTS"), BlockDisposition.EXCLUDED, "front_matter_heading", .9
            elif text in {"references", "bibliography", "glossary", "index"}:
                role, reason, confidence = getattr(StructuralRole, text.upper()), "back_matter_heading", .92
            elif block.evidence_origin == EvidenceOrigin.OCR_INFERRED and block.confidence < .45:
                role, disposition, reason, confidence = StructuralRole.PROBABLE_NOISE, BlockDisposition.REVIEW_REQUIRED, "low_confidence_ocr_text", .6
            result[str(block.id)] = {"disposition": disposition, "role": role, "reason": reason, "confidence": confidence, "evidence": {"page_repetition": len(occurrences[text]) if text else 0}}
        return result

    def _build_nodes(self, blocks, headings, classifications):
        last_sequence = blocks[-1].sequence_number if blocks else 0
        nodes = [NodeCandidate("root", None, HierarchyNodeType.DOCUMENT, StructuralRole.ROOT, "", 0, 0, 0, last_sequence, confidence=.95, strength=HierarchyEvidenceStrength.SOURCE_EXPLICIT)]
        if headings:
            stack: list[tuple[int, str]] = []
            for index, heading in enumerate(headings):
                level = heading.candidate_level
                while stack and stack[-1][0] >= level: stack.pop()
                parent_key = stack[-1][1] if stack else "root"
                next_sequence = next((candidate.block.sequence_number for candidate in headings[index + 1:] if candidate.candidate_level <= level), last_sequence + 1)
                text = heading.candidate_title.lower()
                role = StructuralRole.APPENDIX if text.startswith("appendix") else StructuralRole.REFERENCES if text in {"references", "bibliography"} else StructuralRole.BODY
                node_type = HierarchyNodeType.APPENDIX if role == StructuralRole.APPENDIX else HierarchyNodeType.REFERENCE_GROUP if role == StructuralRole.REFERENCES else HierarchyNodeType.CHAPTER if level == 1 else HierarchyNodeType.SECTION if level == 2 else HierarchyNodeType.SUBSECTION
                key = f"node-{index + 1}"
                owned = [str(block.id) for block in blocks if heading.block.sequence_number <= block.sequence_number < next_sequence and classifications[str(block.id)]["disposition"] != BlockDisposition.EXCLUDED]
                nodes.append(NodeCandidate(key, parent_key, node_type, role, heading.candidate_title, min(level, StructurePolicy.maximum_depth), len(nodes), heading.block.sequence_number, next_sequence - 1, owned, str(heading.block.id), heading.confidence, heading.evidence_strength, {"numbering_pattern": heading.numbering_pattern}))
                stack.append((level, key))
            for node in nodes[1:]:
                node.block_ids = []
            for block in blocks:
                if classifications[str(block.id)]["disposition"] == BlockDisposition.EXCLUDED:
                    continue
                owners = [node for node in nodes[1:] if node.start <= block.sequence_number <= node.end]
                if owners:
                    max(owners, key=lambda node: (node.depth, node.start)).block_ids.append(str(block.id))
        else:
            eligible = [block for block in blocks if classifications[str(block.id)]["disposition"] != BlockDisposition.EXCLUDED]
            groups: list[list[object]] = []
            for block in eligible:
                if not groups or len(groups[-1]) >= StructurePolicy.fallback_blocks_per_group or block.block_type in {ExtractedBlockType.TABLE, ExtractedBlockType.IMAGE}:
                    groups.append([])
                groups[-1].append(block)
            for group in groups:
                first, last = group[0], group[-1]
                node_type = HierarchyNodeType.TABLE_GROUP if first.block_type == ExtractedBlockType.TABLE else HierarchyNodeType.FIGURE_GROUP if first.block_type == ExtractedBlockType.IMAGE else HierarchyNodeType.PARAGRAPH_GROUP
                nodes.append(NodeCandidate(f"fallback-{len(nodes)}", "root", node_type, StructuralRole.BODY, "", 1, len(nodes), first.sequence_number, last.sequence_number, [str(block.id) for block in group], confidence=.6, strength=HierarchyEvidenceStrength.FALLBACK_GENERATED, evidence={"synthetic_title": False}))
        return nodes


class ValidateDocumentHierarchyService:
    def validate(self, nodes, blocks) -> None:
        roots = [node for node in nodes if node.role == StructuralRole.ROOT]
        if len(roots) != 1 or len(nodes) > StructurePolicy.maximum_nodes:
            raise DocumentProcessingError("Hierarchy output is invalid.", "hierarchy_output_invalid")
        keys = {node.key for node in nodes}
        for node in nodes:
            if node.parent_key and node.parent_key not in keys: raise DocumentProcessingError("Hierarchy parent is missing.", "hierarchy_output_invalid")
            if node.start > node.end or node.depth > StructurePolicy.maximum_depth: raise DocumentProcessingError("Hierarchy range or depth is invalid.", "hierarchy_output_invalid")


class ReconstructDocumentHierarchyService:
    def __init__(self, reconstructor=None, validator=None) -> None:
        self.reconstructor = reconstructor or DeterministicHierarchyReconstructor()
        self.validator = validator or ValidateDocumentHierarchyService()

    def execute(self, context):
        job = ContentProcessingJob.objects.get(id=context.job_id)
        if job.status in {JobStatus.CANCELLED, JobStatus.DELETED} or job.cancellation_requested: raise DocumentProcessingError("Processing was cancelled.", "processing_cancelled")
        extraction = DocumentExtraction.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id).order_by("-created_at").first()
        if not extraction: raise DocumentProcessingError("The extraction result is missing.", "extraction_result_missing")
        existing = DocumentHierarchy.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id, document_extraction=extraction, pipeline_version=context.pipeline_version, reconstructor_version=RECONSTRUCTOR_VERSION, configuration_version=STRUCTURE_CONFIGURATION_VERSION).first()
        if existing: return existing, list(existing.nodes.order_by("ordinal")), []
        blocks = list(extraction.blocks.order_by("sequence_number"))
        if not blocks or extraction.source_checksum != extraction.source_document_profile.source_checksum: raise DocumentProcessingError("The extraction result is invalid.", "extraction_result_invalid")
        candidates, classifications, style_profile, warnings = self.reconstructor.reconstruct(blocks)
        self.validator.validate(candidates, blocks)
        canonical = [{"parent": n.parent_key, "type": n.node_type, "role": n.role, "title": n.title, "start": n.start, "end": n.end} for n in candidates]
        checksum = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
        with transaction.atomic():
            hierarchy = DocumentHierarchy.objects.create(job_id=context.job_id, attempt_id=context.attempt_id, resource_id=context.resource_id, stored_file_id=context.stored_file_id, source_document_profile=extraction.source_document_profile, document_extraction=extraction, pipeline_version=context.pipeline_version, reconstructor_name=RECONSTRUCTOR_NAME, reconstructor_version=RECONSTRUCTOR_VERSION, configuration_version=STRUCTURE_CONFIGURATION_VERSION, node_count=len(candidates), maximum_depth=max(n.depth for n in candidates), front_matter_detected=any(v["role"] in {StructuralRole.PREFACE, StructuralRole.COPYRIGHT, StructuralRole.TABLE_OF_CONTENTS} for v in classifications.values()), back_matter_detected=any(v["role"] in {StructuralRole.REFERENCES, StructuralRole.BIBLIOGRAPHY, StructuralRole.GLOSSARY, StructuralRole.INDEX} for v in classifications.values()), navigation_content_detected=any(v["role"] == StructuralRole.TABLE_OF_CONTENTS for v in classifications.values()), noise_candidates_detected=any(v["role"] == StructuralRole.PROBABLE_NOISE for v in classifications.values()), unresolved_block_count=sum(v["disposition"] in {BlockDisposition.UNRESOLVED, BlockDisposition.REVIEW_REQUIRED} for v in classifications.values()), review_recommended=bool(warnings), confidence=.8 if len(candidates) > 1 else .6, warning_count=len(warnings), result_checksum=checksum)
            by_key = {}
            block_by_id = {str(block.id): block for block in blocks}
            for candidate in candidates:
                related = [block_by_id[block_id] for block_id in candidate.block_ids]
                pages = [_page(block) for block in related if _page(block)]
                node = DocumentHierarchyNode.objects.create(document_hierarchy=hierarchy, job_id=context.job_id, attempt_id=context.attempt_id, parent_node=by_key.get(candidate.parent_key), node_type=candidate.node_type, structural_role=candidate.role, title=candidate.title, normalized_title=re.sub(r"\s+", " ", candidate.title).strip(), depth=candidate.depth, ordinal=candidate.ordinal, path=f"/{candidate.key}", start_sequence=candidate.start, end_sequence=candidate.end, source_page_start=min(pages) if pages else None, source_page_end=max(pages) if pages else None, content_block_count=len(related), confidence=candidate.confidence, evidence_strength=candidate.strength, evidence={**candidate.evidence, "style_profile": style_profile if candidate.key == "root" else {}}, metadata={"generated_title": False})
                by_key[candidate.key] = node
                for ordinal, block in enumerate(related):
                    HierarchyNodeBlock.objects.create(document_hierarchy=hierarchy, node=node, extracted_block=block, relationship_role=NodeBlockRole.HEADING if str(block.id) == candidate.heading_block_id else NodeBlockRole.TABLE if block.block_type in {ExtractedBlockType.TABLE, ExtractedBlockType.TABLE_ROW, ExtractedBlockType.TABLE_CELL} else NodeBlockRole.FIGURE if block.block_type == ExtractedBlockType.IMAGE else NodeBlockRole.LIST if block.block_type == ExtractedBlockType.LIST_ITEM else NodeBlockRole.BODY, ordinal=ordinal, included_in_content=True, classification_reason="hierarchy_range_ownership", confidence=candidate.confidence)
            hierarchy.root_node = by_key["root"]
            hierarchy.save(update_fields=["root_node"])
            HierarchyBlockClassification.objects.bulk_create([HierarchyBlockClassification(document_hierarchy=hierarchy, extracted_block=block, disposition=classifications[str(block.id)]["disposition"], structural_role=classifications[str(block.id)]["role"], reason_code=classifications[str(block.id)]["reason"], confidence=classifications[str(block.id)]["confidence"], evidence=classifications[str(block.id)]["evidence"]) for block in blocks])
        return hierarchy, list(hierarchy.nodes.order_by("ordinal")), warnings


class DeterministicSemanticSegmenter:
    def classify(self, blocks, node):
        types = {block.block_type for block in blocks}
        text = "\n\n".join(block.normalized_text for block in blocks if block.normalized_text).strip()
        lowered = f"{node.title}\n{text[:300]}".lower()
        if any(value in types for value in {ExtractedBlockType.TABLE, ExtractedBlockType.TABLE_ROW, ExtractedBlockType.TABLE_CELL}): return SemanticSegmentType.TABLE
        if ExtractedBlockType.IMAGE in types: return SemanticSegmentType.FIGURE
        rules = [("definition", SemanticSegmentType.DEFINITION), ("example", SemanticSegmentType.EXAMPLE), ("case study", SemanticSegmentType.CASE_STUDY), ("theorem", SemanticSegmentType.THEOREM), ("proof", SemanticSegmentType.PROOF), ("summary", SemanticSegmentType.SUMMARY), ("exercise", SemanticSegmentType.EXERCISE), ("question", SemanticSegmentType.QUESTION), ("answer", SemanticSegmentType.ANSWER), ("procedure", SemanticSegmentType.PROCEDURE)]
        for label, segment_type in rules:
            if re.search(rf"\b{re.escape(label)}\b", lowered): return segment_type
        if node.structural_role in {StructuralRole.REFERENCES, StructuralRole.BIBLIOGRAPHY}: return SemanticSegmentType.REFERENCE
        if types == {ExtractedBlockType.LIST_ITEM}: return SemanticSegmentType.LIST
        return SemanticSegmentType.EXPLANATION if len(text) >= SegmentationPolicy.minimum_meaningful_characters else SemanticSegmentType.PARAGRAPH_GROUP

    def groups(self, relationships):
        blocks = [relationship.extracted_block for relationship in relationships if relationship.included_in_content]
        groups, current, size = [], [], 0
        for block in blocks:
            independent = block.block_type in {ExtractedBlockType.TABLE, ExtractedBlockType.IMAGE}
            if current and (independent or size + len(block.normalized_text) > SegmentationPolicy.maximum_characters or len(current) >= SegmentationPolicy.maximum_blocks_per_segment):
                groups.append(current); current=[]; size=0
            current.append(block); size += len(block.normalized_text)
            if independent: groups.append(current); current=[]; size=0
        if current: groups.append(current)
        return groups


class ValidateSemanticSegmentsService:
    def validate(self, candidates) -> None:
        if not candidates: raise DocumentProcessingError("No meaningful semantic segments were produced.", "no_meaningful_segments")
        if len(candidates) > SegmentationPolicy.maximum_segments: raise DocumentProcessingError("The semantic segment limit was exceeded.", "segment_limit_exceeded")


class BuildSemanticSegmentsService:
    def __init__(self, segmenter=None, validator=None) -> None:
        self.segmenter = segmenter or DeterministicSemanticSegmenter()
        self.validator = validator or ValidateSemanticSegmentsService()

    def execute(self, context):
        job = ContentProcessingJob.objects.get(id=context.job_id)
        if job.status in {JobStatus.CANCELLED, JobStatus.DELETED} or job.cancellation_requested: raise DocumentProcessingError("Processing was cancelled.", "processing_cancelled")
        hierarchy = DocumentHierarchy.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id).order_by("-created_at").first()
        if not hierarchy: raise DocumentProcessingError("The hierarchy result is missing.", "hierarchy_unresolved")
        existing = DocumentSegmentation.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id, document_hierarchy=hierarchy, pipeline_version=context.pipeline_version, segmenter_version=SEGMENTER_VERSION, configuration_version=STRUCTURE_CONFIGURATION_VERSION).first()
        if existing: return existing, list(existing.segments.order_by("ordinal")), []
        candidates = []
        for node in hierarchy.nodes.exclude(structural_role=StructuralRole.ROOT).order_by("ordinal"):
            relationships = list(node.block_relationships.select_related("extracted_block").order_by("ordinal"))
            for group in self.segmenter.groups(relationships):
                candidates.append((node, group, self.segmenter.classify(group, node)))
        self.validator.validate(candidates)
        canonical = [{"node": str(node.id), "type": segment_type, "blocks": [block.sequence_number for block in blocks]} for node, blocks, segment_type in candidates]
        checksum = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
        with transaction.atomic():
            segmentation = DocumentSegmentation.objects.create(job_id=context.job_id, attempt_id=context.attempt_id, resource_id=context.resource_id, stored_file_id=context.stored_file_id, document_hierarchy=hierarchy, document_extraction=hierarchy.document_extraction, pipeline_version=context.pipeline_version, segmenter_name=SEGMENTER_NAME, segmenter_version=SEGMENTER_VERSION, configuration_version=STRUCTURE_CONFIGURATION_VERSION, segment_count=len(candidates), body_segment_count=sum(node.structural_role == StructuralRole.BODY for node, _, _ in candidates), excluded_region_count=hierarchy.block_classifications.filter(disposition=BlockDisposition.EXCLUDED).count(), unresolved_content_count=hierarchy.unresolved_block_count, review_recommended=hierarchy.review_recommended, confidence=hierarchy.confidence, warning_count=0, result_checksum=checksum)
            segments = []
            for ordinal, (node, blocks, segment_type) in enumerate(candidates):
                text = "\n\n".join(block.normalized_text for block in blocks if block.normalized_text).strip()
                pages = [_page(block) for block in blocks if _page(block)]
                segment = SemanticSegment(document_segmentation=segmentation, document_hierarchy=hierarchy, hierarchy_node=node, job_id=context.job_id, attempt_id=context.attempt_id, resource_id=context.resource_id, segment_type=segment_type, title=node.title, normalized_text=text, ordinal=ordinal, source_block_start=blocks[0].sequence_number, source_block_end=blocks[-1].sequence_number, source_page_start=min(pages) if pages else None, source_page_end=max(pages) if pages else None, confidence=.9 if segment_type in {SemanticSegmentType.TABLE, SemanticSegmentType.FIGURE} else .78, evidence_strength=SegmentationEvidenceStrength.STRUCTURE_DERIVED if node.evidence_strength != HierarchyEvidenceStrength.FALLBACK_GENERATED else SegmentationEvidenceStrength.FALLBACK_GENERATED, evidence={"classification": "deterministic_rules"}, metadata={"source_method_counts": dict(Counter(block.source_method for block in blocks)), "ocr_present": any(block.evidence_origin == EvidenceOrigin.OCR_INFERRED for block in blocks)})
                segment.full_clean(); segment.save(); segments.append(segment)
                SemanticSegmentBlock.objects.bulk_create([SemanticSegmentBlock(document_segmentation=segmentation, semantic_segment=segment, extracted_block=block, relationship_role=SegmentBlockRole.TABLE if block.block_type in {ExtractedBlockType.TABLE, ExtractedBlockType.TABLE_ROW, ExtractedBlockType.TABLE_CELL} else SegmentBlockRole.FIGURE if block.block_type == ExtractedBlockType.IMAGE else SegmentBlockRole.LIST if block.block_type == ExtractedBlockType.LIST_ITEM else SegmentBlockRole.BODY, ordinal=index) for index, block in enumerate(blocks)])
        return segmentation, segments, []


class LegacyHierarchySectionProjectionService:
    """Temporary ParsedSection projection; durable hierarchy remains authoritative."""

    def __init__(self, hierarchy: DocumentHierarchy) -> None:
        self.hierarchy = hierarchy

    def detect_sections(self, parsed_document):
        from apps.content_intelligence.domain.models import ParsedSection
        sections = []
        eligible = self.hierarchy.nodes.filter(structural_role__in=[StructuralRole.BODY, StructuralRole.APPENDIX]).exclude(node_type=HierarchyNodeType.DOCUMENT).order_by("start_sequence", "ordinal")
        for node in eligible:
            segments = node.semantic_segments.order_by("ordinal")
            body = "\n\n".join(segment.normalized_text for segment in segments if segment.normalized_text).strip()
            if not body:
                continue
            origin = "fallback_generated" if node.evidence_strength == HierarchyEvidenceStrength.FALLBACK_GENERATED else "source_explicit" if node.evidence_strength == HierarchyEvidenceStrength.SOURCE_EXPLICIT else "inferred_hierarchy"
            title = node.title or f"Source group {len(sections) + 1}"
            sections.append(ParsedSection(parsed_document=parsed_document, heading=title[:255], body_text=body, sequence_number=len(sections) + 1, section_type=ParsedSection.SectionType.APPENDIX if node.structural_role == StructuralRole.APPENDIX else ParsedSection.SectionType.CHAPTER, confidence=node.confidence, metadata={"section_origin": origin, "document_hierarchy_id": str(self.hierarchy.id), "hierarchy_node_id": str(node.id), "source_page_start": node.source_page_start, "source_page_end": node.source_page_end, "synthetic_title": not bool(node.title)}))
        return sections
