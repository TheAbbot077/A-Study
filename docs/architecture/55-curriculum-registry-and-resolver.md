# PI-6F.2 Curriculum registry and resolver

## Boundary

PI-6F.2 is implemented inside the `self_study` bounded context because it
resolves an activated PI-6F.1 intent and its immutable effective-policy
snapshot. Registry records are distinct from `academic.Curriculum`, which
represents populated institutional learning content.

The package does not download curricula, extract concepts, build graphs,
diagnose learners, acquire teaching material, or generate an autonomous
curriculum. Its final established-curriculum selection is PI-6F.3 input.

## Registry

`CurriculumAuthority` records authority identity separately from explicit
verification. Unverified, rejected, suspended, or inactive authorities cannot
support automatic selection.

`CurriculumReference` is the continuing curriculum identity.
`CurriculumVersion` holds version-specific provenance and availability. Once a
version is active, resolution-relevant fields are immutable. Corrections
require a new version and provenance.

Only governance actors may create or change registry state. Global registry
governance requires a superuser. Tenant registry governance uses the existing
institution administrator/owner roles and remains tenant-scoped.

## Deterministic resolution

Resolver algorithm `pi-6f.2-rules-v1` evaluates:

1. Learner-supplied official curriculum
2. Institution or qualification curriculum
3. National or regional curriculum
4. Professional or accreditation framework
5. Approved curated reference
6. Governed composite proposal
7. Durable failure

Hard constraints are applied before ranking. Version status, authority trust,
provenance, policy source permission, licence, institutional scope,
effective dates, jurisdiction, subject, and language path are recorded for
every candidate. A high score cannot overcome a hard rejection.

Eligible candidates are ordered first by hierarchy rank, then explicit
preference within that hierarchy, deterministic component score, and stable
version identifier. A lower hierarchy cannot displace a viable higher source.

The learner-visible response contains governed classifications and reason
codes, not internal model prompts or hidden reasoning.

## Language

Every candidate records one of:

- `NATIVE_LANGUAGE`
- `OFFICIAL_TRANSLATION`
- `GENERATED_TRANSLATION_REQUIRED`

Generated translation permission does not create or misrepresent an official
curriculum version. Translation happens outside PI-6F.2.

## Attempts, composites, and failure

One attempt exists per intent version and resolver version. The Celery task
receives only its attempt identifier, claims the row transactionally, and is
safe to replay after a terminal result.

Every evaluated candidate is retained. Selection decisions are immutable.
A composite proposal contains independently valid component versions and
roles but does not merge content. Approval is required before it becomes final.

`CurriculumResolutionFailure` now references an exhausted attempt, immutable
policy snapshot, resolver version, registry fingerprint, candidate rejections,
and completion time. PI-6F.1 autonomous fallback accepts only such a failure
for the same active intent and policy snapshot.

## Events

Final events are published after durable commit:

- `curriculum.authority_created`
- `curriculum.authority_verified`
- `curriculum.authority_suspended`
- `curriculum.reference_created`
- `curriculum.version_created`
- `curriculum.version_activated`
- `curriculum.version_superseded`
- `curriculum.version_suspended`
- `curriculum.resolution_started`
- `curriculum.selection_awaiting_approval`
- `curriculum.selected`
- `curriculum.composite_proposed`
- `curriculum.composite_approved`
- `curriculum.composite_rejected`
- `curriculum.resolution_failed`

Candidate evaluation is durable internal state and does not produce a
high-volume external event.

## Validation

```powershell
docker compose exec -T backend python manage.py makemigrations --check
docker compose exec -T backend python manage.py migrate
docker compose exec -T backend pytest apps/self_study/tests/test_curriculum_resolution_domain.py -q
docker compose exec -T backend pytest apps/self_study/tests/test_curriculum_resolution_services.py -q
docker compose exec -T backend pytest apps/self_study/tests/test_curriculum_resolution_api.py apps/self_study/tests/test_curriculum_resolution_task.py -q
docker compose exec -T frontend node --test ./scripts/audit-routes.test.mjs
```
