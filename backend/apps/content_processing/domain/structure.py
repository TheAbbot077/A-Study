from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.content_processing.domain.extraction import sanitize_source_text


class HierarchyNodeType(models.TextChoices):
    DOCUMENT = "document", "Document"
    PART = "part", "Part"
    CHAPTER = "chapter", "Chapter"
    SECTION = "section", "Section"
    SUBSECTION = "subsection", "Subsection"
    TOPIC_GROUP = "topic_group", "Topic Group"
    PARAGRAPH_GROUP = "paragraph_group", "Paragraph Group"
    LIST_GROUP = "list_group", "List Group"
    TABLE_GROUP = "table_group", "Table Group"
    FIGURE_GROUP = "figure_group", "Figure Group"
    APPENDIX = "appendix", "Appendix"
    REFERENCE_GROUP = "reference_group", "Reference Group"
    EXERCISE_GROUP = "exercise_group", "Exercise Group"
    UNKNOWN = "unknown", "Unknown"


class StructuralRole(models.TextChoices):
    ROOT = "root", "Root"
    BODY = "body", "Body"
    FRONT_MATTER = "front_matter", "Front Matter"
    BACK_MATTER = "back_matter", "Back Matter"
    NAVIGATION = "navigation", "Navigation"
    TITLE_PAGE = "title_page", "Title Page"
    COPYRIGHT = "copyright", "Copyright"
    DEDICATION = "dedication", "Dedication"
    PREFACE = "preface", "Preface"
    FOREWORD = "foreword", "Foreword"
    ACKNOWLEDGEMENTS = "acknowledgements", "Acknowledgements"
    TABLE_OF_CONTENTS = "table_of_contents", "Table Of Contents"
    LIST_OF_FIGURES = "list_of_figures", "List Of Figures"
    LIST_OF_TABLES = "list_of_tables", "List Of Tables"
    GLOSSARY = "glossary", "Glossary"
    BIBLIOGRAPHY = "bibliography", "Bibliography"
    REFERENCES = "references", "References"
    INDEX = "index", "Index"
    APPENDIX = "appendix", "Appendix"
    SUMMARY = "summary", "Summary"
    EXERCISE = "exercise", "Exercise"
    ASSESSMENT = "assessment", "Assessment"
    BOILERPLATE = "boilerplate", "Boilerplate"
    PROBABLE_NOISE = "probable_noise", "Probable Noise"
    UNCLASSIFIED = "unclassified", "Unclassified"


class HierarchyEvidenceStrength(models.TextChoices):
    SOURCE_EXPLICIT = "source_explicit", "Source Explicit"
    STRONGLY_INFERRED = "strongly_inferred", "Strongly Inferred"
    HEURISTICALLY_INFERRED = "heuristically_inferred", "Heuristically Inferred"
    FALLBACK_GENERATED = "fallback_generated", "Fallback Generated"
    UNRESOLVED = "unresolved", "Unresolved"


class BlockDisposition(models.TextChoices):
    INCLUDED = "included", "Included"
    EXCLUDED = "excluded", "Excluded"
    REVIEW_REQUIRED = "review_required", "Review Required"
    UNRESOLVED = "unresolved", "Unresolved"


class NodeBlockRole(models.TextChoices):
    HEADING = "heading", "Heading"
    BODY = "body", "Body"
    CAPTION = "caption", "Caption"
    TABLE = "table", "Table"
    FIGURE = "figure", "Figure"
    LIST = "list", "List"
    SUPPORTING = "supporting", "Supporting"
    EXCLUDED = "excluded", "Excluded"
    UNRESOLVED = "unresolved", "Unresolved"


class SemanticSegmentType(models.TextChoices):
    OVERVIEW = "overview", "Overview"
    DEFINITION = "definition", "Definition"
    EXPLANATION = "explanation", "Explanation"
    EXAMPLE = "example", "Example"
    PROCEDURE = "procedure", "Procedure"
    CASE_STUDY = "case_study", "Case Study"
    THEOREM = "theorem", "Theorem"
    PROOF = "proof", "Proof"
    FORMULA = "formula", "Formula"
    TABLE = "table", "Table"
    FIGURE = "figure", "Figure"
    SUMMARY = "summary", "Summary"
    EXERCISE = "exercise", "Exercise"
    QUESTION = "question", "Question"
    ANSWER = "answer", "Answer"
    REFERENCE = "reference", "Reference"
    LIST = "list", "List"
    PARAGRAPH_GROUP = "paragraph_group", "Paragraph Group"
    MIXED_CONTENT = "mixed_content", "Mixed Content"
    UNKNOWN = "unknown", "Unknown"


class SegmentationEvidenceStrength(models.TextChoices):
    SOURCE_EXPLICIT = "source_explicit", "Source Explicit"
    STRUCTURE_DERIVED = "structure_derived", "Structure Derived"
    LEXICALLY_INFERRED = "lexically_inferred", "Lexically Inferred"
    FALLBACK_GENERATED = "fallback_generated", "Fallback Generated"
    UNRESOLVED = "unresolved", "Unresolved"


class SegmentBlockRole(models.TextChoices):
    TITLE = "title", "Title"
    BODY = "body", "Body"
    TABLE = "table", "Table"
    FIGURE = "figure", "Figure"
    CAPTION = "caption", "Caption"
    LIST = "list", "List"
    FORMULA = "formula", "Formula"
    SUPPORTING_CONTEXT = "supporting_context", "Supporting Context"


class DocumentHierarchy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="document_hierarchies")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="document_hierarchies")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.SET_NULL, null=True, blank=True, related_name="document_hierarchies")
    stored_file = models.ForeignKey("storage.StoredFile", on_delete=models.PROTECT, related_name="document_hierarchies")
    source_document_profile = models.ForeignKey("content_processing.SourceDocumentProfile", on_delete=models.PROTECT, related_name="hierarchies")
    document_extraction = models.ForeignKey("content_processing.DocumentExtraction", on_delete=models.PROTECT, related_name="hierarchies")
    pipeline_version = models.CharField(max_length=100)
    reconstructor_name = models.CharField(max_length=128)
    reconstructor_version = models.CharField(max_length=64)
    configuration_version = models.CharField(max_length=64)
    root_node = models.OneToOneField("content_processing.DocumentHierarchyNode", on_delete=models.PROTECT, null=True, blank=True, related_name="root_for_hierarchy")
    node_count = models.PositiveIntegerField(default=0)
    maximum_depth = models.PositiveIntegerField(default=0)
    front_matter_detected = models.BooleanField(default=False)
    back_matter_detected = models.BooleanField(default=False)
    navigation_content_detected = models.BooleanField(default=False)
    noise_candidates_detected = models.BooleanField(default=False)
    unresolved_block_count = models.PositiveIntegerField(default=0)
    review_recommended = models.BooleanField(default=False)
    confidence = models.FloatField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    result_checksum = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "content_processing_document_hierarchy"
        constraints = [
            models.UniqueConstraint(fields=["job", "attempt", "document_extraction", "pipeline_version", "reconstructor_version", "configuration_version"], name="cp_hierarchy_identity_unique"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_hierarchy_confidence_range"),
        ]


class DocumentHierarchyNode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_hierarchy = models.ForeignKey(DocumentHierarchy, on_delete=models.CASCADE, related_name="nodes")
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="hierarchy_nodes")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="hierarchy_nodes")
    parent_node = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    node_type = models.CharField(max_length=32, choices=HierarchyNodeType.choices)
    structural_role = models.CharField(max_length=32, choices=StructuralRole.choices)
    title = models.CharField(max_length=512, blank=True)
    normalized_title = models.CharField(max_length=512, blank=True)
    depth = models.PositiveIntegerField()
    ordinal = models.PositiveIntegerField()
    path = models.CharField(max_length=512)
    start_sequence = models.PositiveIntegerField()
    end_sequence = models.PositiveIntegerField()
    source_page_start = models.PositiveIntegerField(null=True, blank=True)
    source_page_end = models.PositiveIntegerField(null=True, blank=True)
    content_block_count = models.PositiveIntegerField(default=0)
    confidence = models.FloatField(default=0)
    evidence_strength = models.CharField(max_length=32, choices=HierarchyEvidenceStrength.choices)
    evidence = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_hierarchy_node"
        ordering = ["ordinal"]
        constraints = [
            models.UniqueConstraint(fields=["document_hierarchy", "ordinal"], name="cp_hierarchy_node_ordinal_unique"),
            models.UniqueConstraint(fields=["document_hierarchy", "path"], name="cp_hierarchy_node_path_unique"),
            models.UniqueConstraint(fields=["document_hierarchy"], condition=models.Q(structural_role=StructuralRole.ROOT), name="cp_hierarchy_one_root"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_hierarchy_node_confidence_range"),
            models.CheckConstraint(condition=models.Q(end_sequence__gte=models.F("start_sequence")), name="cp_hierarchy_node_range_valid"),
        ]

    def clean(self) -> None:
        if self.structural_role == StructuralRole.ROOT and self.parent_node_id:
            raise ValidationError("The hierarchy root cannot have a parent.")
        if self.parent_node_id and self.parent_node.document_hierarchy_id != self.document_hierarchy_id:
            raise ValidationError("Parent and child must belong to one hierarchy.")
        if self.parent_node_id and self.parent_node.depth >= self.depth:
            raise ValidationError("A parent must be shallower than its child.")
        if self.end_sequence < self.start_sequence or not 0 <= self.confidence <= 1:
            raise ValidationError("Hierarchy node range or confidence is invalid.")


class HierarchyNodeBlock(models.Model):
    document_hierarchy = models.ForeignKey(DocumentHierarchy, on_delete=models.CASCADE, related_name="node_block_relationships")
    node = models.ForeignKey(DocumentHierarchyNode, on_delete=models.CASCADE, related_name="block_relationships")
    extracted_block = models.ForeignKey("content_processing.ExtractedBlock", on_delete=models.PROTECT, related_name="hierarchy_relationships")
    relationship_role = models.CharField(max_length=32, choices=NodeBlockRole.choices)
    ordinal = models.PositiveIntegerField()
    included_in_content = models.BooleanField(default=True)
    classification_reason = models.CharField(max_length=128)
    confidence = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_hierarchy_node_block"
        constraints = [models.UniqueConstraint(fields=["node", "extracted_block", "relationship_role"], name="cp_node_block_unique")]


class HierarchyBlockClassification(models.Model):
    document_hierarchy = models.ForeignKey(DocumentHierarchy, on_delete=models.CASCADE, related_name="block_classifications")
    extracted_block = models.ForeignKey("content_processing.ExtractedBlock", on_delete=models.PROTECT, related_name="structural_classifications")
    disposition = models.CharField(max_length=32, choices=BlockDisposition.choices)
    structural_role = models.CharField(max_length=32, choices=StructuralRole.choices)
    reason_code = models.CharField(max_length=128)
    confidence = models.FloatField(default=0)
    evidence = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_hierarchy_block_classification"
        constraints = [models.UniqueConstraint(fields=["document_hierarchy", "extracted_block"], name="cp_block_classification_unique")]


class DocumentSegmentation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="document_segmentations")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="document_segmentations")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.SET_NULL, null=True, blank=True, related_name="document_segmentations")
    stored_file = models.ForeignKey("storage.StoredFile", on_delete=models.PROTECT, related_name="document_segmentations")
    document_hierarchy = models.ForeignKey(DocumentHierarchy, on_delete=models.PROTECT, related_name="segmentations")
    document_extraction = models.ForeignKey("content_processing.DocumentExtraction", on_delete=models.PROTECT, related_name="segmentations")
    pipeline_version = models.CharField(max_length=100)
    segmenter_name = models.CharField(max_length=128)
    segmenter_version = models.CharField(max_length=64)
    configuration_version = models.CharField(max_length=64)
    segment_count = models.PositiveIntegerField(default=0)
    body_segment_count = models.PositiveIntegerField(default=0)
    excluded_region_count = models.PositiveIntegerField(default=0)
    unresolved_content_count = models.PositiveIntegerField(default=0)
    review_recommended = models.BooleanField(default=False)
    confidence = models.FloatField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    result_checksum = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "content_processing_document_segmentation"
        constraints = [
            models.UniqueConstraint(fields=["job", "attempt", "document_hierarchy", "pipeline_version", "segmenter_version", "configuration_version"], name="cp_segmentation_identity_unique"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_segmentation_confidence_range"),
        ]


class SemanticSegment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_segmentation = models.ForeignKey(DocumentSegmentation, on_delete=models.CASCADE, related_name="segments")
    document_hierarchy = models.ForeignKey(DocumentHierarchy, on_delete=models.PROTECT, related_name="semantic_segments")
    hierarchy_node = models.ForeignKey(DocumentHierarchyNode, on_delete=models.PROTECT, related_name="semantic_segments")
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="semantic_segments")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="semantic_segments")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.SET_NULL, null=True, blank=True, related_name="semantic_segments")
    segment_type = models.CharField(max_length=32, choices=SemanticSegmentType.choices)
    title = models.CharField(max_length=512, blank=True)
    normalized_text = models.TextField(blank=True)
    ordinal = models.PositiveIntegerField()
    source_block_start = models.PositiveIntegerField()
    source_block_end = models.PositiveIntegerField()
    source_page_start = models.PositiveIntegerField(null=True, blank=True)
    source_page_end = models.PositiveIntegerField(null=True, blank=True)
    character_count = models.PositiveIntegerField(default=0)
    word_count = models.PositiveIntegerField(default=0)
    token_estimate = models.PositiveIntegerField(default=0)
    confidence = models.FloatField(default=0)
    evidence_strength = models.CharField(max_length=32, choices=SegmentationEvidenceStrength.choices)
    evidence = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_semantic_segment"
        ordering = ["ordinal"]
        constraints = [
            models.UniqueConstraint(fields=["document_segmentation", "ordinal"], name="cp_segment_ordinal_unique"),
            models.CheckConstraint(condition=models.Q(source_block_end__gte=models.F("source_block_start")), name="cp_segment_range_valid"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_segment_confidence_range"),
        ]

    def clean(self) -> None:
        self.normalized_text = sanitize_source_text(self.normalized_text)
        self.character_count = len(self.normalized_text)
        self.word_count = len(self.normalized_text.split())
        self.token_estimate = max(0, (self.character_count + 3) // 4)
        if self.source_block_end < self.source_block_start or not 0 <= self.confidence <= 1:
            raise ValidationError("Semantic segment range or confidence is invalid.")
        if not self.normalized_text and self.segment_type not in {SemanticSegmentType.TABLE, SemanticSegmentType.FIGURE}:
            raise ValidationError("Textual semantic segments require text.")


class SemanticSegmentBlock(models.Model):
    document_segmentation = models.ForeignKey(DocumentSegmentation, on_delete=models.CASCADE, related_name="segment_block_relationships")
    semantic_segment = models.ForeignKey(SemanticSegment, on_delete=models.CASCADE, related_name="block_relationships")
    extracted_block = models.ForeignKey("content_processing.ExtractedBlock", on_delete=models.PROTECT, related_name="semantic_relationships")
    relationship_role = models.CharField(max_length=32, choices=SegmentBlockRole.choices)
    ordinal = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_semantic_segment_block"
        constraints = [models.UniqueConstraint(fields=["semantic_segment", "extracted_block", "relationship_role"], name="cp_segment_block_unique")]
