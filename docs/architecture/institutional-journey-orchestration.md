# Institutional Journey Orchestration

PI-8B.4 extends the governed `LearningJourney` engine to institutional learners.

The governing principle is:

```text
Authority determines the journey.
The journey determines learning.
Teaching remains shared.
```

Institutional orchestration does not duplicate self-study teaching, evidence, mastery, competency progression, remediation, or journey evolution. It changes the authority provider that establishes the journey.

## Authority providers

The journey layer now resolves authority through providers:

- `SelfStudyAuthorityProvider`
- `InstitutionAuthorityProvider`

Shared services ask who governs the journey instead of branching deeply on origin.

## Assignment projection

`InstitutionalLearningAssignment` is a projection of institutional authority into a learner journey. It references existing project authority:

- `Institution`
- `InstitutionMembership`
- optional `Subject`
- optional `CurriculumReference`
- `LearningJourney`

It does not introduce programme, cohort, offering, registrar, transcript, or certification source-of-truth models.

## Runtime convergence

Once assigned, the institutional journey feeds the same runtime as other journeys:

```text
Institutional assignment
→ LearningJourney
→ CompetencyProgressionService
→ JourneyEvolutionService
→ LearningPlanEvolutionService
→ shared teaching runtime
```

Institutional authority determines required competencies and delivery objectives. It does not create institutional mastery or institutional evidence engines.
