# Abbot Study Product Constitution

## Product Name

Abbot Study

## Product Vision

Abbot Study is an AI-native education operating system that understands curriculum, understands learners, and guides each student through ordered, mastery-based learning with The Abbot, Ariel, assessments, remediation, and intelligent review.

## Core Mission

To help learners master any textbook or curriculum through a structured, personalized, AI-supported learning journey.

## Non-Negotiable Learning Rules

1. Learning order must never depend on async processing order.
2. Learning order must never depend on database IDs.
3. Learning order must never depend on timestamps.
4. Learning order must never depend on Celery queue completion order.
5. Learning order must never be secretly changed by AI.
6. Chapters must use explicit sequence numbers.
7. Concepts must use explicit sequence numbers.
8. A learner may only unlock the next concept after mastering the current concept.
9. AI may enrich learning, but it may not bypass mastery.
10. Admin-approved curriculum is the source of official learning truth.

## Core Roles

### Student

The learner who studies concepts, answers assessments, teaches Ariel, and progresses through mastery.

### The Abbot

The AI tutor that teaches the current unlocked concept using source-grounded explanations.

### Ariel

The student AI companion. Ariel only knows what the student has successfully taught it.

### Admin

The human authority responsible for reviewing curriculum, parser output, AI-generated material, quality warnings, and system health.

### Institution

A future school, university, company, or training provider that manages learners, teachers, curricula, and analytics.

## Core Learning Flow

1. Student creates account.
2. Student creates subject.
3. Student uploads textbook or curriculum material.
4. System processes the document.
5. Chapters and concepts are extracted in order.
6. Admin reviews and approves curriculum where required.
7. Student begins with the first unlocked concept.
8. The Abbot teaches the concept.
9. Student asks follow-up questions if needed.
10. Student completes assessment.
11. Passing unlocks the next concept.
12. Failing triggers remediation.
13. Student teaches Ariel after mastering concepts.
14. System tracks mastery, forgetting, weaknesses, and recommendations.

## AI Authority Boundaries

AI may:

- explain concepts
- simplify concepts
- generate examples
- generate diagrams
- generate assessments
- evaluate teach-back
- recommend review
- detect misconceptions
- summarize curriculum
- assist admins
- generate draft learning assets

AI may not:

- secretly reorder official curriculum
- unlock concepts without mastery
- approve official curriculum without admin rules
- override explicit sequence numbers
- hide uncertainty
- teach future locked concepts as if they are current
- replace admin review for high-impact content

## Source Grounding Rule

The Abbot must use trusted curriculum content first.

General knowledge may only be used as clarification and should be clearly separated from textbook-grounded material where appropriate.

## Curriculum Rule

Raw parser output is not the same as official curriculum.

The system may produce draft curriculum, but official learning content must come from approved, versioned curriculum structures.

## Assessment Rule

Assessments must test the current concept only unless explicitly configured otherwise by an approved curriculum rule.

## Ariel Rule

The Abbot teaches the student.

The student teaches Ariel.

Ariel represents the learner's understanding and should not know content that the learner has not mastered or taught.

## Admin Trust Rule

Every powerful AI feature must be observable, reviewable, and reversible.

## Cost Rule

The first build prioritizes correctness and learning quality.

Cost optimization comes later through caching, model routing, smaller models, batch generation, and heuristic fallbacks.

## Codex Rule

Codex will not be introduced during the foundation phase.

Codex may later assist with implementation, tests, refactoring, scaffolding, and documentation.

Codex must not independently decide learning rules, curriculum authority, unlock logic, or AI boundaries.

## Long-Term Destination

Abbot Study should grow from a textbook study app into an AI University Operating System that can support schools, universities, professional training, oral exams, interview preparation, and lifelong learning.