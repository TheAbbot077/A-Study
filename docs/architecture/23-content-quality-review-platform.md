# 23 - Content Quality & Review Platform

## Status

PI-3H implementation.

## Purpose

The Content Quality & Review Platform gives trusted academic workflows a service-layer process for reviewing canonical Content Sections and Content Concepts.

The platform supports human review state, quality marking, approval metadata, and business events. It does not publish learner-facing content or enforce learner progression gates yet.

## Scope

PI-3H extends:

* ContentSection
* ContentConcept

New review fields:

* review_status
* quality_status
* review_notes
* approved_at
* approved_by

The service layer introduces ContentReviewService.

## Review Status

Supported review_status values:

* draft
* in_review
* approved
* rejected
* archived

Default value:

* draft

## Quality Status

Supported quality_status values:

* unknown
* low
* acceptable
* high
* needs_attention

Default value:

* unknown

## Service Operations

ContentReviewService supports section review operations:

* submit_section_for_review
* approve_section
* reject_section
* mark_section_quality

ContentReviewService supports concept review operations:

* submit_concept_for_review
* approve_concept
* reject_concept
* mark_concept_quality

## Behavior

Submitting for review sets review_status to in_review.

Approving content sets:

* review_status to approved
* approved_at
* approved_by

Rejecting content sets:

* review_status to rejected

Rejecting content clears approved_at and approved_by.

Marking quality updates quality_status.

review_notes stores the latest supplied notes.

## Business Events

The service publishes business events for review actions:

* academic.content_section_submitted_for_review
* academic.content_section_approved
* academic.content_section_rejected
* academic.content_section_quality_marked
* academic.content_concept_submitted_for_review
* academic.content_concept_approved
* academic.content_concept_rejected
* academic.content_concept_quality_marked

Events describe review facts. They do not publish content or unlock learner access.

## Non-Goals

PI-3H does not implement:

* Frontend UI
* DRF APIs
* Django admin actions
* AI quality reviewers
* Lesson review
* Assessment review
* Learner-facing publication gates
* Learner progress behavior

## Architectural Boundary

ContentReviewService is a service-layer capability for trusted academic workflows.

Approval marks content as academically approved, but publication and learner-facing access remain separate future capabilities.
