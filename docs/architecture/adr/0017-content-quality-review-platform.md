# Content Quality & Review Platform

## Status
Accepted

## Context

Abbot Study requires human oversight for official academic content. Manual authoring and importer contracts can create or propose canonical structure, but Content Sections and Content Concepts need review and quality states before future publication workflows can rely on them.

The Product Constitution requires human authority over curriculum, lessons, assessments, and quality decisions. The Canonical Domain Language defines Review, Approval, and Quality Review as administrative concepts that determine publication readiness.

## Decision

We will extend ContentSection and ContentConcept with review and quality fields:

* review_status
* quality_status
* review_notes
* approved_at
* approved_by

review_status supports:

* draft
* in_review
* approved
* rejected
* archived

quality_status supports:

* unknown
* low
* acceptable
* high
* needs_attention

We will introduce ContentReviewService in the academic services layer. The service manages submit, approve, reject, and quality marking operations for sections and concepts.

The service publishes business events:

* academic.content_section_submitted_for_review
* academic.content_section_approved
* academic.content_section_rejected
* academic.content_section_quality_marked
* academic.content_concept_submitted_for_review
* academic.content_concept_approved
* academic.content_concept_rejected
* academic.content_concept_quality_marked

## Consequences

* Canonical academic content can carry human review and quality state.
* Approval metadata is captured directly on Content Sections and Content Concepts.
* Future publication gates can build on approved review state without redefining review semantics.
* PI-3H remains scoped away from APIs, UI, AI review, lesson review, assessment review, and learner-facing access control.
