# 21 - Importer Contracts

## Status

PI-3F implementation.

## Purpose

Importer Contracts define the boundary between external source material and canonical academic content.

Importers may convert supplied material into proposed Content Sections and Content Concepts. They do not own the Academic Domain, do not publish curriculum, and do not persist imported content.

## Scope

PI-3F introduces:

* ContentImporter
* ContentImportResult
* ImportedSection
* ImportedConcept
* ManualContentImporter

The implementation is intentionally limited to contracts, validation, and structured manual transformation.

## Non-Goals

PI-3F does not introduce:

* PDF parsing
* OCR
* AI extraction
* Celery tasks
* Database persistence
* ResourceIngestionJob lifecycle changes
* Frontend UI
* Publication or approval workflows

## Contract Model

### ContentImporter

ContentImporter is the stable interface future importers must implement.

Required methods:

* can_import(source)
* import_content(source, context=None)

Importers return ContentImportResult rather than writing database records.

### ImportedSection

ImportedSection represents a proposed Content Section.

Fields:

* title
* description
* sequence_number
* metadata
* concepts

### ImportedConcept

ImportedConcept represents a proposed Content Concept.

Fields:

* title
* description
* learning_objective
* sequence_number
* metadata

### ContentImportResult

ContentImportResult represents the outcome of an import attempt.

Fields:

* success
* sections
* warnings
* errors
* metadata

Failed results preserve errors and do not require imported sections.

## Validation Rules

Importer outputs must preserve ordered learning structure:

* Section sequence numbers must be greater than or equal to 1.
* Section sequence numbers must be unique within a result.
* Concept sequence numbers must be greater than or equal to 1.
* Concept sequence numbers must be unique within each section.

These validation rules protect the Academic Domain from unordered or ambiguous imported structure.

## Manual Importer

ManualContentImporter accepts structured mappings that already describe sections and concepts.

It exists to exercise the contract and support future manual authoring flows. It does not create ContentSection or ContentConcept records.

## Architectural Boundary

Importers produce academic content proposals.

The Academic Domain owns educational meaning.

Administrative approval and publication remain separate future capabilities.
