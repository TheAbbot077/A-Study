# Importer Contracts

## Status
Accepted

## Context

Abbot Study needs a stable boundary for converting external material into canonical academic structure. Future importers may support PDFs, documents, publisher APIs, manual authoring, or AI-assisted extraction, but none of those mechanisms should define educational rules or persist official content directly.

The Product Constitution requires human authority over official curriculum and lessons. The Canonical Domain Language states that importers produce academic content while the Academic Domain owns educational meaning.

## Decision

We will introduce importer contracts inside the academic capability.

The contract includes:

* ContentImporter
* ContentImportResult
* ImportedSection
* ImportedConcept

ContentImporter exposes can_import(source) and import_content(source, context=None). Importers return ContentImportResult instances containing proposed ImportedSection and ImportedConcept structures.

The contract validates ordered academic structure:

* Section sequence numbers must be greater than or equal to 1.
* Section sequence numbers must be unique within a result.
* Concept sequence numbers must be greater than or equal to 1.
* Concept sequence numbers must be unique within each section.

A ManualContentImporter may transform structured input into ContentImportResult for tests and future manual authoring support.

## Consequences

* Future importers can target a consistent canonical structure.
* Import mechanisms remain separate from academic approval and publication.
* The ResourceIngestionJob lifecycle remains unchanged.
* No database persistence is introduced for importer output in PI-3F.
* Future PDF, OCR, and AI extraction work can build on this contract without redefining academic terminology.
