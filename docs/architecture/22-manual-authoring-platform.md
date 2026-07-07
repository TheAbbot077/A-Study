# 22 - Manual Authoring Platform

## Status

PI-3G implementation.

## Purpose

The Manual Authoring Platform allows trusted administrative workflows to create and manage canonical academic content through the service layer.

Manual authoring works with existing Academic Domain models:

* ContentSection
* ContentConcept

The capability does not introduce frontend UI, DRF APIs, Django admin actions, approval workflows, or learner progress behavior.

## Scope

PI-3G introduces ManualAuthoringService in the academic services layer.

Supported operations:

* create_section
* update_section
* archive_section
* reorder_section
* create_concept
* update_concept
* archive_concept
* reorder_concept

## Constraints

Manual authoring preserves canonical ordering rules:

* Section sequence numbers must be greater than or equal to 1.
* Concept sequence numbers must be greater than or equal to 1.
* Section sequence numbers remain unique per LearningResource.
* Concept sequence numbers remain unique per ContentSection.

Database constraints remain the final guard for uniqueness.

## Reordering Strategy

Reordering is explicit. Callers must request a new sequence number directly.

If the requested sequence number is occupied, the service uses a predictable swap strategy:

1. Move the edited item to a temporary sequence number after the current maximum.
2. Move the conflicting item into the edited item's previous sequence number.
3. Move the edited item into the requested sequence number.

This avoids broad implicit reordering and keeps the user's requested sequence number intact.

## Business Events

Manual authoring publishes business events for meaningful actions:

* academic.manual_section_created
* academic.manual_section_updated
* academic.manual_section_archived
* academic.manual_section_reordered
* academic.manual_concept_created
* academic.manual_concept_updated
* academic.manual_concept_archived
* academic.manual_concept_reordered

Events describe completed business facts. They do not approve or publish content.

## Non-Goals

PI-3G does not implement:

* Frontend authoring UI
* DRF authoring APIs
* Django admin actions
* AI-generated content
* PDF parsing
* Content quality approval
* Learner progress
* Curriculum publication

## Architectural Boundary

ManualAuthoringService is a service-layer capability for trusted workflows.

It creates and manages canonical academic content, but official approval and publication remain separate future capabilities.
