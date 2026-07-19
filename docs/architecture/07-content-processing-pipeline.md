# 07 - Content Processing Pipeline

## Purpose

PI-6C.1 introduces a dedicated Content Processing bounded context between uploaded files and downstream content-intelligence stages.

This layer owns orchestration state. It does not own academic truth, teaching readiness policy, or parsing quality.

## Responsibilities

The Content Processing Platform is responsible for:

* durable processing-job lifecycle
* immutable attempt history
* deterministic stage ordering
* stage progress reporting
* typed failures
* retry policy
* cooperative cancellation
* deletion terminality
* Celery stage dispatch
* stage-result durability
* safe compatibility projection into the legacy content-intelligence API

It is not responsible for:

* semantic parsing quality
* final academic review decisions
* retrieval indexing implementation details beyond stage orchestration
* teaching readiness inference

## Aggregate

### ContentProcessingJob

`ContentProcessingJob` is the aggregate root.

It tracks:

* resource identity
* stored-file identity
* pipeline version
* current stage
* terminal status
* progress
* active attempt number
* cancellation state
* failure presentation
* transition timestamps

Status and stage are separated intentionally.

### Job Status

Terminal and top-level lifecycle status:

* `active`
* `ready_for_review`
* `ready_for_teaching`
* `failed`
* `cancelled`
* `deleted`

### Processing Stage

Active pipeline stages:

* `created`
* `queued`
* `inspecting`
* `extracting`
* `structuring`
* `segmenting`
* `validating`
* `populating`
* `indexing`

## Attempt History

Every retry creates a new immutable `ProcessingAttempt`.

Attempts preserve:

* attempt number
* trigger
* restart stage
* correlation identifiers
* failure outcome
* timestamps

Only the active attempt may advance the aggregate.

This protects the platform from stale Celery deliveries and late worker completions.

## Diagnostics

`ProcessingDiagnostic` stores append-only stage diagnostics.

Each diagnostic belongs to both:

* a job
* an attempt

Safe public messages can flow to polling clients. Internal details remain persistence-level diagnostics for operational inspection.

## Stage Results

`ProcessingStageResult` is the durable idempotency envelope for a completed stage.

It records:

* job
* attempt
* stage
* pipeline version
* result version
* idempotency key
* output references
* checksum

This is the foundation for future stage-specific output models in PI-6C.2 through PI-6C.5.

## Retry Policy

Retry behavior is centralized.

The policy determines:

* whether retry is allowed
* maximum attempts
* restart stage
* retry classification

Business-visible retries create new attempts. They are not hidden inside Celery autoretry behavior.

## Cancellation

Cancellation is cooperative.

The platform:

1. records cancellation intent durably
2. blocks future dispatch from newer transitions
3. rechecks cancellation after stage execution
4. prevents the next stage from being dispatched when cancellation wins

## Deletion Semantics

Deletion is terminal.

When an import is deleted:

* the processing job is marked `deleted`
* future retries are blocked
* stale workers must not advance the job
* legacy import state must not be resurrected

The content-intelligence deletion flow remains the owner of storage and academic cleanup. Content Processing owns orchestration finality.

## Celery Role

Celery is an execution adapter only.

One task executes one stage. Task payloads contain identifiers:

* `job_id`
* `attempt_id`
* `expected_stage`
* optional `correlation_id`

Celery does not own lifecycle fields and does not apply business transitions directly.

## Idempotency and Concurrency

PI-6C.1 protects processing state through:

* active-job identity lookup
* expected-attempt validation
* expected-stage validation
* durable stage-result uniqueness
* row-lock repository access
* post-execution state revalidation
* deletion and cancellation checks

## Legacy Compatibility

The existing Content Intelligence parser remains temporarily wrapped behind a compatibility stage processor.

For PI-6C.1:

* the legacy parser still performs the actual parsing and academic population work
* the new platform owns orchestration and retry/cancel lifecycle
* legacy import-job status is now a one-way projection from `ContentProcessingJob`

Compatibility mapping:

* `created` or `queued` -> legacy `pending`
* active processing stages -> legacy `processing`
* `ready_for_review` -> legacy `processing` compatibility value plus authoritative `processing_status=ready_for_review` and `review_required=true`
* `ready_for_teaching` -> legacy `completed`
* `failed` -> legacy `failed`
* `cancelled` -> legacy `cancelled`

## Readiness Boundary

Processing success stops at `ready_for_review`.

`ready_for_teaching` is explicit and separate. It is not inferred automatically from extraction success.

This keeps teaching-readiness policy outside the parser.

## Frontend Contract

The existing import-job polling contract remains available and now projects:

* processing job id
* active stage
* progress
* stage label
* active attempt number
* warning count
* retry/cancel flags

This keeps the frontend thin while allowing the new orchestration layer to become authoritative.

### Governed review pause

`READY_FOR_REVIEW` is terminal for automatic processing but not terminal for the full publication lifecycle. Technical document processing and proposal validation have completed successfully; the state is neither active processing nor failure. Population and retrieval indexing remain pending until an authorized proposal decision satisfies the governance boundary.

Status consumers resolve lifecycle state in this order: the authoritative `ContentProcessingJob` status, proposal/review state, then the legacy import status. The legacy status remains compatibility metadata and must not keep polling active when the authoritative job is ready for review. Polling stops at `ready_for_review`, `ready_for_teaching`, `failed`, `cancelled`, and `deleted`.

The ordinary import status response may expose bounded proposal summary counts and confidence. Proposed sections and concepts are recommendations, not Academic Platform records. Published and study-available counts remain zero until approved population completes, and teaching readiness additionally requires retrieval readiness. A progress value of 98% at the review gate represents publication and indexing still pending; it must be presented as “Ready for academic review,” not as an active 98% processing state.

## PI-6C.2 Layout-Aware Inspection and Extraction

`INSPECTING` now creates an immutable `SourceDocumentProfile`. Detection combines extension, declared MIME type, magic bytes, OOXML package structure, and parser verification. Profiles retain source checksum, inspector version, encryption/corruption state, PDF native/scanned/mixed classification, OCR policy, page recommendations, warnings, and confidence.

`EXTRACTING` creates one versioned `DocumentExtraction` and a deterministic, ordered `ExtractedBlock` collection. Blocks are source evidence only: they preserve page references, coordinates when truthfully available, typography/style hints, table and image references, evidence origin, confidence, and source method. They never create academic sections, concepts, semantic segments, retrieval chunks, or readiness decisions.

PDF native text is preferred. Scanned PDFs require OCR; mixed PDFs use OCR only for weak pages. OCR evidence is explicitly marked and does not replace trustworthy native evidence. Tesseract and Poppler remain infrastructure adapters and their absence is a typed operational condition.

DOCX extraction walks the document body XML so paragraphs and tables remain interleaved. Paragraph styles are durable hints; table parents, rows, and cells remain structural evidence. Page geometry is omitted when DOCX does not expose it rather than invented.

Inspection and extraction identities include the job, attempt, source checksum, pipeline version, and adapter version. Stage results contain only profile/extraction identifiers and checksums. A later attempt creates new immutable evidence. Full extracted text is excluded from diagnostics, events, and ordinary polling responses.

Legacy flattened text is a deterministic compatibility projection of ordered blocks. Existing parser-driven academic population remains temporarily isolated in the later compatibility processor until PI-6C.3/PI-6C.4 replace it. PI-6C.3 owns hierarchy reconstruction and final header/footer interpretation.

## Deferred Work

The following remain deferred beyond PI-6C.1:

* hierarchy reconstruction from durable layout evidence
* improved structural extraction
* advanced indexing
* explicit review approval workflow
* final teaching-readiness decision engine
* richer stage processors for PI-6C.2 through PI-6C.5

## PI-6C.3 Hierarchy Reconstruction and Semantic Segmentation

`STRUCTURING` consumes the active `SourceDocumentProfile`, `DocumentExtraction`, and ordered `ExtractedBlock` collection. It never reparses the source file. The stage creates a versioned `DocumentHierarchy`, exactly one document root, ordered hierarchy nodes, node-to-block ownership relationships, and a classification for every extracted block.

Reconstruction begins with document-wide style analysis. Explicit DOCX heading styles and source heading types outrank numbering and PDF typography; numbering, font size, boldness, source order, and nearby body evidence are combined conservatively. Dates, page numbers, URLs, email addresses, filenames, table cells, weak OCR, repeated margin text, TOC entries, and synthetic labels are rejected or down-ranked as headings.

Front matter, tables of contents, references, appendices, page numbers, and repeated headers remain durable classifications. High-confidence noise is excluded only from body ownership; extraction rows are never deleted. TOC evidence can support diagnostics but never directly creates duplicate body nodes. When trustworthy headings are absent, page/source-order-aware paragraph, table, and figure groups are generated with `fallback_generated` evidence rather than one synthetic “Imported Content” section.

`SEGMENTING` consumes hierarchy nodes and their ordered block relationships. Hierarchy boundaries come first, followed by table/figure/list boundaries and safe size boundaries. Semantic types include definitions, explanations, examples, procedures, case studies, theorem/proof/formula material, tables, figures, summaries, exercises, questions, answers, references, lists, paragraph groups, and mixed content. Deterministic rules work without an external model.

Every semantic segment records its hierarchy node, source block range, page range, character/word/token estimates, confidence, evidence strength, and explicit segment-to-block relationships. Tables and figures remain independent evidence. OCR/native provenance is retained in bounded metadata. Semantic segments are neither concepts nor retrieval chunks.

Hierarchy identity includes job, attempt, extraction, pipeline, reconstructor, and configuration versions. Segmentation identity similarly includes its hierarchy and segmenter/configuration versions. Database constraints and PI-6C.1 stage-result uniqueness make both stages replay-safe.

For temporary compatibility, eligible body hierarchy nodes and semantic segments project into legacy `ParsedSection` objects in source order. The projection does not own lifecycle state and does not make academic acceptance decisions. PI-6C.4 owns import proposals and the retirement path for legacy academic population.

## PI-6C.4 Academic Import Proposals and Population

PI-6C.6 hardens the boundary before population. Early dotted-leader entries establish a bounded TOC region, including intervening navigation lines and split page-number forms; early publication month/year and standalone Roman page markers remain excluded front matter. TOC titles are reconciled canonically against body headings and material mismatches require review.

Semantic segmentation preserves heading and body relationships separately. Each segment records body-block counts, substantive body character counts, supporting body block identifiers, and an explicit heading-only marker. Heading-only segments cannot qualify as explanations or concepts.

Proposal validation applies blocking evidence, canonical-duplicate, absolute-quantity, and page-ratio rules. Automatic acceptance is a versioned policy evaluation requiring no blocking findings, no upstream review recommendation, no proposal review requirement, and sufficient aggregate confidence. Ineligible proposals stop at `READY_FOR_REVIEW`; population requires an approval decision newer than the latest validation snapshot. Legacy projection remains compatibility-only; authoritative status and explicit review metadata prevent its `processing` value from being interpreted as active work.

`VALIDATING` is the governed boundary between document interpretation and academic truth. It consumes the active `DocumentHierarchy` and `DocumentSegmentation` and creates a versioned `AcademicImportProposal`. The deterministic proposal engine recommends sections and concepts; it never writes Academic Platform records.

Each `ProposedSection` references its hierarchy node. Each `ProposedConcept` references an eligible semantic segment and requires meaningful supporting text. `ProposalEvidence` connects every proposed item to hierarchy, semantic segment, extracted blocks, pages, evidence strength, and bounded reasoning metadata. Headings, TOC entries, dates, references, malformed fallback labels, empty text, and unsupported segments cannot independently become concepts.

Proposal governance uses independent review and population state machines. Review states include draft, ready, under review, approved, approved with edits, rejected, superseded, and archived. Approval produces a durable `ProposalDecision`; it does not itself publish content. Existing automatic imports remain compatible through an explicit recorded compatibility review decision rather than direct parser population.

## PI-6C.5 Retrieval Platform

Retrieval is a versioned projection of approved Academic Platform content, never an authority for curriculum. The `INDEXING` stage consumes a completed `AcademicPopulationJob`, its approved proposal mappings, approved `ContentSection` and `ContentConcept` records, and their traceable `SemanticSegment` evidence. It never reads parser output directly.

`RetrievalChunkBuilder` applies the centralized `ChunkPolicy`. Academic, concept, and semantic boundaries are preferred; token limits refine those boundaries using sentence units. Every durable chunk carries institution, subject, resource, section, concept, semantic segment, proposal, population, page, policy, retrieval, and embedding provenance. Its checksum and identity are deterministic across replay. A `RetrievalChunkCollection` groups one population version.

The framework-independent `EmbeddingProvider` and `RetrievalIndex` ports isolate providers. The default compatibility implementation stores opaque vectors in PostgreSQL JSON and performs deterministic hybrid ranking. `PostgreSQLPgvectorRetrievalIndex` contains the optional pgvector-specific capability probe and distance expression; deployments may select it after provisioning the extension without changing domain or application services.

Hybrid retrieval combines vector similarity, keyword overlap, and institution-scoped Academic metadata filters under a versioned `RankingPolicy`. Filters cover institution, subject, resource, section, concept, proposal/population versions, pages, and chunk type. Embeddings and ranking internals are never exposed by the public API.

`BuildGroundingPackageService` is the exclusive Retrieval-to-Teaching boundary. It applies filters and token budgets, persists ranked chunk references, confidence scores, rationale, statistics and diagnostics, and creates durable citations back through all Academic and processing provenance. Teaching work remains deferred.

Readiness is `NOT_INDEXED`, `INDEXING`, `INDEXED`, `STALE`, or `FAILED`. Population completion and successful indexing are both required before the processing job becomes `READY_FOR_TEACHING`. `RetrievalIndexJob` identity is population + retrieval version + embedding version; chunk identity additionally includes proposal version and policy version. Replays update rather than duplicate projections and publish collection-, embedding-, index-, readiness-, and grounding-level summary events.

`POPULATING` accepts only an approved proposal in `ready_for_population`. An `AcademicPopulationJob` owns publication and records created/updated section and concept counts, versions, checksum, warnings, failure state, and timestamps. Proposed items retain one-to-one mappings to their published Academic records, making replay and retries idempotent. Reprocessing can update existing ordered records without duplicating them.

Published sections and concepts inherit the approved governance decision and retain proposal provenance. The learning resource activation behavior remains compatible. Population does not index content, create retrieval chunks, or mark teaching readiness; `INDEXING` remains a compatibility boundary until PI-6C.5.
# PI-6D.1 Review Handoff

`READY_FOR_REVIEW` is consumed by the Academic Proposal Review bounded context. Approval writes an `ApprovedProposalProjection` and dispatches the existing `POPULATING` stage after transaction commit. Population rejects approved proposals that lack a matching projection checksum. Reprocessing creates a new processing attempt and preserves the superseded proposal and review history.

PI-6D.2 supersedes the direct approval-to-population dispatch described above. Reviewed approval now stops at an immutable projection with status `READY_FOR_POPULATION`. It publishes `academic_review.ready_for_population`; PI-6D.3 will consume that event and projection. No approval HTTP request or PI-6D.2 application service invokes population.
