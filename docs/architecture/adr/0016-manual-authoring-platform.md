# Manual Authoring Platform

## Status
Accepted

## Context

Abbot Study needs a trusted service-layer capability for manually creating and managing canonical academic content. Importer Contracts allow external material to be transformed into proposed structure, but administrators also need a direct authoring path for Content Sections and Content Concepts.

The Product Constitution requires human oversight of curriculum, lessons, assessments, and quality decisions. ASEM v2 requires business behavior to live in services, with framework concerns kept outside the domain.

## Decision

We will introduce ManualAuthoringService inside the academic services layer.

The service will manage existing canonical academic models:

* ContentSection
* ContentConcept

The service supports create, update, archive, and explicit reorder operations for sections and concepts.

Manual authoring publishes business events:

* academic.manual_section_created
* academic.manual_section_updated
* academic.manual_section_archived
* academic.manual_section_reordered
* academic.manual_concept_created
* academic.manual_concept_updated
* academic.manual_concept_archived
* academic.manual_concept_reordered

Reordering uses an explicit swap strategy when the requested sequence number is already occupied:

1. Move the edited item to a temporary sequence number after the current maximum.
2. Move the conflicting item into the edited item's previous sequence number.
3. Move the edited item into the requested sequence number.

## Consequences

* Trusted workflows can create and manage canonical academic content without APIs or UI.
* Manual content changes become observable through business events.
* Ordering remains explicit and protected by service validation plus database uniqueness constraints.
* Approval, publication, content quality review, AI generation, and learner progress remain outside PI-3G.
