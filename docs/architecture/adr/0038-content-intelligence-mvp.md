# ADR 0038: Content Intelligence MVP

## Status

Accepted.

## Context

The Academic Platform already owns subjects, learning resources, sections, and concepts.

Program Increment 6 begins the Content Intelligence Platform, whose responsibility is to transform raw uploaded files into structured academic candidates without taking ownership of academic truth.

The platform needed a first production-ready slice that supports common educational file formats and produces useful import diagnostics while preserving Academic as the system of record.

## Decision

Create a new `apps.content_intelligence` capability.

Model parsing artifacts with:

* `ContentImportJob`
* `ParsedDocument`
* `ParsedSection`
* `ParsedConceptCandidate`
* `ContentExtractionResult`
* `ContentValidationFinding`
* `ParserPipelineRun`

Implement deterministic services for:

* import coordination
* extraction
* section detection
* concept extraction
* confidence scoring
* validation
* end-to-end pipeline orchestration

Use OCR only as an explicit fallback.

Populate Academic content through Academic application services rather than parser-owned ORM writes.

## Consequences

Content Intelligence becomes a separate bounded capability rather than an extension hidden inside Academic.

The pipeline is format-extensible without changing orchestration logic.

Imported resources can become teachable content while preserving clear academic ownership boundaries.

Future PI-6 capabilities can add richer OCR, HTML/EPUB adapters, publisher connectors, and stronger structural interpretation without redesigning the ingestion artifact model.

## Non-Goals

PI-6A does not implement:

* AI extraction
* publisher-specific parsing
* LMS adapters
* HTML/EPUB imports
* advanced OCR engines
* frontend content-intelligence dashboards
