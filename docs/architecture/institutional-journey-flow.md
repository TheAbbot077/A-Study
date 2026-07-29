# Institutional Journey Flow

PI-8B.1 adds structural institutional journey support only.

It uses the current authority models in `users.domain.models`:

- `Institution`;
- `InstitutionMembership`;
- `InstitutionRole`;
- `InstitutionType`.

The increment does not move these models.

## Supported now

An institutional journey may be created when:

- the institution is active;
- the learner has active membership;
- the actor has institutional authority through membership or superuser status.

The initial projection remains intentionally limited:

- state: `SUBJECT_BINDING_REQUIRED`;
- blocker: `INSTITUTIONAL_ASSIGNMENT_REQUIRED`.

## Deferred

Later PI-8B increments should introduce:

- course offerings;
- cohorts;
- enrolments;
- institutional delivery plans;
- educator assignments;
- institutional assessments;
- interventions;
- completion approvals.

PI-8B.1 does not fabricate course offering identifiers or institutional learning plans.
