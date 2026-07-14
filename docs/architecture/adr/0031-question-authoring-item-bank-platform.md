# ADR 0031: Question Authoring & Item Bank Platform

## Status

Accepted.

## Context

PI-5A established assessment records. PI-5B established evidence and mastery decisions. PI-5C established assessment strategies and blueprints.

PI-5D needs reusable assessment item infrastructure so authored items can be reviewed, quality marked, optioned, and attached to assessments without creating questions automatically.

## Decision

Add persisted item bank models:

* `ItemBankEntry`
* `ItemOption`
* `AssessmentItemBankLink`

Use `ItemBankService` as the sole business mutation boundary for item creation, review lifecycle, quality marking, option management, and assessment linking.

Keep item bank entries separate from `AssessmentItem`. `AssessmentItem` remains the PI-5A assessment foundation record, while `AssessmentItemBankLink` allows reusable item bank entries to be ordered inside an assessment.

Register and publish:

* `assessment.item_bank_entry_created`
* `assessment.item_bank_entry_updated`
* `assessment.item_bank_entry_archived`
* `assessment.item_bank_entry_submitted_for_review`
* `assessment.item_bank_entry_approved`
* `assessment.item_bank_entry_rejected`
* `assessment.item_bank_entry_quality_marked`
* `assessment.item_option_added`
* `assessment.item_option_updated`
* `assessment.item_option_removed`
* `assessment.item_added_to_assessment`
* `assessment.item_removed_from_assessment`

## Consequences

Reusable item authoring is now separated from assessment attempts and learner responses.

Assessments can reference reusable item bank entries without copying authored content.

Future question generation, grading, and mastery workflows can consume item bank content without owning authoring lifecycle behavior.

## Non-Goals

PI-5D does not implement:

* AI question generation
* grading
* mastery updates
* remediation
* learner progression
* frontend UI
