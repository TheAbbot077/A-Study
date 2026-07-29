# Competency Progression

PI-8B.3 makes learner progression competency-centric.

The progression chain is:

```text
governed evidence
→ mastery decision
→ competency progression
→ journey evolution
→ learning-plan evolution request
```

`LearningCompetencyProgress` is the durable state for one governed curriculum competency inside one `LearningJourney`. The governed competency reference is `self_study.CurriculumNode`; progression does not create curriculum, subjects, grades, certificates, or institutional advancement.

## Lifecycle

Progression states are:

- `NOT_STARTED`
- `EMERGING`
- `DEVELOPING`
- `DEMONSTRATED`
- `REINFORCED`
- `REVIEW_REQUIRED`
- `REGRESSED`
- `SUPERSEDED`

Unlock states are:

- `LOCKED`
- `AVAILABLE`
- `ACTIVE`
- `COMPLETED`
- `SUPERSEDED`

Only one active progress record may exist per journey and competency.

## Authority boundary

The progression engine does not score assessments and does not infer mastery from activity. Lesson views, elapsed time, page reads, and session completion are not sufficient progression evidence.

Progression consumes existing `assessments.MasteryDecision` records. The mastery bounded context remains authoritative for interpreting evidence.

## History

`LearningCompetencyProgressHistory` records every transition with:

- old and new progression state;
- old and new unlock state;
- transition reason;
- triggering mastery decision;
- triggering evidence identifier when available;
- actor and timestamp.

History is append-only. Superseded competencies remain visible through history instead of being deleted.

## Events

Progression publishes identifier-only events:

- `learning_competency.emerging`
- `learning_competency.demonstrated`
- `learning_competency.reinforced`
- `learning_competency.review_required`
- `learning_competency.regressed`
- `learning_competency.superseded`

These events describe governed state changes. They do not certify grades or institutional credit.
