# Question Authoring & Item Bank Platform

## Status

Implemented for PI-5D.

## Purpose

The Question Authoring & Item Bank Platform provides reusable, reviewable assessment items for the Evidence of Learning Platform.

PI-5D creates item bank infrastructure for human-authored or externally authored reusable items. It does not generate questions with AI, grade responses, update mastery, remediate learners, unlock progression, or create frontend UI.

## Scope

PI-5D implements:

* `ItemBankEntry`
* `ItemOption`
* `AssessmentItemBankLink`
* `ItemDifficulty`
* `ItemReviewStatus`
* `ItemQualityStatus`
* `ItemBankService`

## Item Bank Entry

`ItemBankEntry` stores reusable assessment item content for a Content Concept.

It includes:

* Content Concept
* item type
* prompt
* explanation
* difficulty
* review status
* quality status
* nullable author
* metadata
* timestamps

Supported difficulty values:

* `unknown`
* `easy`
* `medium`
* `hard`
* `advanced`

Supported review statuses:

* `draft`
* `in_review`
* `approved`
* `rejected`
* `archived`

Supported quality statuses:

* `unknown`
* `low`
* `acceptable`
* `high`
* `needs_attention`

## Item Options

`ItemOption` stores ordered answer choices or structured options for an `ItemBankEntry`.

Options preserve authoring data only. `is_correct` is metadata for future grading workflows and does not grade learner responses in PI-5D.

Constraints:

* option sequence numbers start at `1`
* option sequence numbers are unique per item bank entry

## Assessment Links

`AssessmentItemBankLink` attaches reusable item bank entries to an `Assessment`.

Links preserve assessment ordering without copying item content.

Constraints:

* link sequence numbers start at `1`
* link sequence numbers are unique per assessment
* the same item bank entry cannot be linked to the same assessment twice

## Service Boundary

`ItemBankService` owns all item bank mutations.

Service methods:

* `create_item`
* `update_item`
* `archive_item`
* `submit_item_for_review`
* `approve_item`
* `reject_item`
* `mark_item_quality`
* `add_option`
* `update_option`
* `remove_option`
* `list_items_for_concept`
* `add_item_to_assessment`
* `remove_item_from_assessment`
* `list_items_for_assessment`

The service does not create generated questions, grade learner responses, or update mastery state.

## Events

The service publishes:

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

## Architectural Boundaries

PI-5D does not include:

* AI question generation
* grading
* mastery updates
* remediation
* learner progression
* frontend UI

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py migrate
docker compose exec backend pytest apps/assessments
```
