# Institutional Authority

PI-8B.4 uses the current institutional authority models:

- `Institution`
- `InstitutionMembership`
- `InstitutionRole`
- `InstitutionType`

`InstitutionalLearningAssignment` coordinates those models with a learner journey. The assignment can carry institution-facing projection labels such as programme and course, but those labels are not a registrar or SIS.

## Provider behavior

`InstitutionAuthorityProvider` determines:

- the institution governing the journey;
- the learner under assignment;
- subject and curriculum authority when assigned;
- read/progression/completion permissions.

Institutional staff can see only policy-approved institutional journey information. Learners retain access to their own journey.

## Compatibility

Older membership-bound institutional journeys remain projectable. New institutional journeys should bind through `LearningJourneySourceType.INSTITUTIONAL_ASSIGNMENT`.
