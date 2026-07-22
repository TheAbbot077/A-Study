# PI-6F.3 Curriculum and Competency Graph

PI-6F.3 turns a terminal PI-6F.2 curriculum selection, or an approved composite, into a durable and reproducible graph. It does not diagnose a learner, map learning resources, download sources, construct a teaching path, or declare teaching readiness.

## Authority and lifecycle

`CurriculumGraph` retains the selected intent and exactly one authoritative source: an immutable selection decision or an approved composite proposal. `CurriculumGraphVersion` freezes the selection fingerprint, builder, validator, stable-key algorithm, construction method, counts, validation result, and graph fingerprint. Publication requires a matching fingerprint and a passed validation run with no unresolved blocker. Published content is immutable; corrections create a later version. Withdrawal or critical provenance changes create an explicit invalidation rather than rewriting history.

Only active selected curriculum versions can start construction. Structured import, curated authoring, and approved composite assembly are supported. Free-form model output is not an authoritative graph specification, and a client cannot submit scores, validation results, findings, or fingerprints.

## Identity, semantics, and citations

Node keys are deterministic hashes of the selected curriculum version, normalized authority namespace, external identifier, node type, structural path, and title. Edge keys include typed endpoints and requirement semantics; symmetric relations canonicalize endpoint order. The graph stores curriculum roots, stages, modules, topics, outcomes, concepts, competencies, assessment objectives, and explicit external prerequisites.

Edges distinguish structure (`PART_OF`), required/recommended/optional prerequisites (`REQUIRES`), outcome support (`SATISFIES`), assessment alignment, ordering, equivalence, specialization, bridging, and conflicts. Document adjacency alone cannot establish a required prerequisite.

Every authoritative node and every consequential relationship retains a citation to one of the selected curriculum versions, including source URI, structured locator, language, citation type, confidence, rationale, and builder version. Generated or derived structure cannot be represented as explicit source content.

## Validation and traversal

Validation is deterministic and persisted. Blockers include missing or multiple roots, missing outcomes, structural or required-prerequisite cycles, orphan nodes, unsupported outcomes, unaligned competencies, citation gaps, invalid provenance, unsupported required-edge derivation, and unresolved composite conflicts. Unresolved external prerequisites are visible warnings and never become inferred mastery.

Traversal is bounded to 25 levels, cycle-safe, tenant/owner guarded at the API boundary, and ordered by curriculum ordinal plus stable identity. The API exposes graph/version summaries, ordered nodes, required prerequisite closure, and validation findings. It does not expose hidden prompts or permit arbitrary unbounded graph queries.

## Orchestration and events

The persisted specification is committed before `self_study.build_curriculum_graph` receives a graph-version identifier. A completed build commits before `self_study.validate_curriculum_graph` receives the same identifier. Both tasks are idempotent at terminal states. Durable lifecycle events cover build start, specification persistence, build completion, validation failure/readiness, publication, and invalidation.

## Manual diagnostics

Use repository validation policy and run these manually when authorized:

```powershell
docker compose exec -T backend python manage.py makemigrations --check
docker compose exec -T backend python manage.py migrate
docker compose exec -T backend pytest apps/self_study/tests/test_curriculum_graph_domain.py apps/self_study/tests/test_curriculum_graph_tasks.py -q
docker compose exec -T backend pytest apps/self_study/tests -q
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npm run smoke:audit:test
```
