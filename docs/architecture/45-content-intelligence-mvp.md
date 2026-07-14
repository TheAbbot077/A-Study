# 45 - Content Intelligence MVP

## Purpose

PI-6A introduces the Content Intelligence Platform as the first capability of Program Increment 6.

The platform ingests raw learning-resource files and transforms them into structured academic candidates that can populate the Academic Platform.

The Academic Platform remains the system of record.

Content Intelligence treats imported files as raw evidence rather than academic truth.

---

## Scope

PI-6A supports:

* `PDF` imports
* `DOCX` imports
* deterministic text extraction
* explicit OCR fallback
* section detection
* concept-candidate extraction
* deterministic confidence scoring
* structured validation findings
* academic content population through Academic services

PI-6A does not support:

* EPUB imports
* HTML imports
* publisher APIs
* LMS adapters
* AI extraction
* academic ownership of parsed artifacts

---

## Canonical Models

### ContentImportJob

The top-level import record for one `LearningResource`.

Tracks lifecycle state, format, OCR decisions, confidence scores, and diagnostics.

### ParsedDocument

The normalized parsed representation of one imported file.

### ParsedSection

A structured section candidate detected from the parsed document.

### ParsedConceptCandidate

A concept candidate extracted from a parsed section.

### ContentExtractionResult

The recorded extraction output, including extraction method, normalized text, OCR usage, and text sufficiency.

### ContentValidationFinding

A structured validation issue produced by the pipeline.

### ParserPipelineRun

An execution record for one pipeline run against a content import job.

---

## Pipeline Lifecycle

1. Import job created
2. Extraction attempted
3. OCR requested if text is insufficient
4. Sections detected
5. Concept candidates extracted
6. Confidence scores computed
7. Validation findings generated
8. Academic Platform populated
9. Import job completed or failed

---

## OCR Decision Flow

PI-6A uses OCR as a fallback only.

Flow:

* extract text
* if extracted text is sufficient, continue
* if extracted text is insufficient, request OCR
* record OCR request
* record OCR completion
* continue pipeline with OCR-derived text

This decision is explicit in `ContentImportJob` and `ContentExtractionResult`.

---

## Service Responsibilities

### ImportService

Creates and retries import jobs.

### ExtractionService

Resolves file format and extracts normalized text from `PDF` and `DOCX`.

### SectionDetectionService

Detects logical sections from normalized document text.

### ConceptExtractionService

Builds structured concept candidates from section bodies.

### ConfidenceScoringService

Produces deterministic extraction, section, concept, and structural scores.

### ValidationService

Produces structured findings for missing sections, duplicate headings, empty concepts, abnormal section sizes, and extraction anomalies.

### PipelineService

Coordinates the end-to-end import pipeline and populates Academic content through `LearningContentService`.

---

## Academic Integration

Content Intelligence never owns:

* `LearningResource`
* `ContentSection`
* `ContentConcept`

Instead, PI-6A populates those through the existing Academic application services.

This keeps parsing concerns outside the Academic Platform while still enabling imported resources to become teachable content.

---

## Event Flow

Published events:

* `content_intelligence.import_started`
* `content_intelligence.extraction_completed`
* `content_intelligence.ocr_requested`
* `content_intelligence.ocr_completed`
* `content_intelligence.sections_detected`
* `content_intelligence.concepts_extracted`
* `content_intelligence.import_validated`
* `content_intelligence.academic_population_completed`
* `content_intelligence.import_completed`
* `content_intelligence.import_failed`

Consumed integration hooks:

* `storage.file_uploaded`
* `academic.learning_resource_created`

The current subscribers are lightweight extension points that preserve clean future automation paths without baking orchestration into event adapters.

---

## Repository Boundaries

PI-6A introduces repository abstractions for:

* import jobs
* parsed documents
* extraction results
* validation findings
* pipeline runs

This keeps pipeline orchestration separated from persistence mapping and aligns with the repo's stronger later-increment architecture conventions.

---

## API Surface

Primary API resource:

* `/api/content-intelligence/import-jobs/`

Supported operations:

* create import job
* list import jobs
* retrieve import job
* retrieve parsed outline
* retrieve validation findings
* retry failed import

---

## Admin Surface

Admin support includes:

* import jobs
* parsed documents
* parsed sections
* parsed concept candidates
* extraction results
* validation findings
* pipeline runs

This provides operational visibility before a dedicated content-intelligence UI exists.

---

## Known Limitations

PI-6A intentionally keeps extraction deterministic and conservative.

Known limitations:

* OCR is a fallback placeholder rather than full OCR engine integration
* PDF extraction quality depends on available extractable text and optional parser availability
* section detection is heuristic rather than publisher-specific
* concept extraction is candidate-oriented and intentionally simple
* retry currently reuses the same import job record rather than branching into a new job lineage
