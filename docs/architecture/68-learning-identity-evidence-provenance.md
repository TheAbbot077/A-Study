# PI-7B.2 — Governed Learning Identity Evidence and Provenance

PI-7B.2 extends the Learning Identity bounded context with governed evidence links and provenance readiness.

The key invariant is:

> Learning Identity records why an attribute is believed; it does not become the owner of the underlying evidence.

Source-domain records remain authoritative. Learning Identity stores typed, resolved references and lifecycle state, not copied assessment answers, diagnostic responses, learning-session transcripts, institutional notes, or onboarding conversations.

## Compatibility with PI-7B.1

PI-7B.1 already represented simple declaration origin directly on `LearningIdentityAttribute` through `source_type`, `source_reference`, `declared_at`, `created_by`, and visibility fields.

PI-7B.2 keeps that as the compatibility path for declared attributes. A declared attribute can still publish when it has valid declaration provenance on the attribute itself.

External, confirming, contradicting, superseding, and contextual evidence is represented by `LearningIdentityEvidenceLink`.

This avoids two competing systems:

- attribute-level fields represent simple declaration origin;
- evidence links represent governed external/source-domain provenance.

## Evidence-link model

`LearningIdentityEvidenceLink` belongs to exactly one `LearningIdentityAttribute`.

It records:

- controlled source domain and source type;
- opaque source identifier and source revision;
- relationship;
- authority class;
- lifecycle status;
- observation/validity/freshness metadata;
- bounded weight and confidence contribution;
- safe summary and visibility;
- withdrawal, invalidation, and supersession lifecycle metadata.

Evidence identity fields are not edited through admin or ordinary services. Lifecycle changes preserve history.

## External-reference design

Evidence references use:

```text
source_domain
source_type
source_identifier
source_revision
```

The identifier is opaque outside the owning bounded context. Learning Identity does not use generic foreign keys and does not directly couple the domain model to every source-domain model.

## Resolver port and registry

The application layer depends on a resolver port:

```python
LearningIdentityEvidenceSourceResolver.resolve(...)
```

Resolvers return only safe provenance metadata:

- source existence and lifecycle;
- tenant and learner ownership;
- authority class;
- observation and validity dates;
- source revision;
- safe summary and visibility.

Resolvers do not return raw evidence payloads or ORM model instances.

The resolver registry fails closed for unsupported domain/type combinations and rejects duplicate registrations.

Initial adapters:

- `LEARNING_IDENTITY / LEARNER_DECLARATION`
- `INSTITUTION / INSTITUTIONAL_MEMBERSHIP`

Other source types are intentionally unsupported until later slices define safe adapters.

## Relationships and authority

Evidence relationships:

- `SUPPORTS`
- `CONTRADICTS`
- `CONFIRMS`
- `SUPERSEDES`
- `CONTEXTUALIZES`

Authority classes:

- `DECLARATIVE`
- `INSTITUTIONAL`
- `ASSESSMENT`
- `DIAGNOSTIC`
- `OBSERVATIONAL`
- `DERIVED`
- `SYSTEM`

Declarative sources cannot confirm verified attributes. Institutional and other authoritative sources may confirm only through explicit policy.

## Lifecycle

Evidence statuses:

- `ACTIVE`
- `STALE`
- `WITHDRAWN`
- `INVALIDATED`
- `SUPERSEDED`

Lifecycle changes update the evidence link and may mark the attribute or profile for review. They do not mutate historical attribute values or profile-version publication facts.

## Provenance readiness

Profile-version provenance evaluates to:

- `READY`
- `NEEDS_REVIEW`
- `BLOCKED`

Readiness uses stable reason codes such as:

- `DECLARATION_SOURCE_REQUIRED`
- `AUTHORITATIVE_EVIDENCE_REQUIRED`
- `GOVERNED_EVIDENCE_REQUIRED`
- `DERIVATION_POLICY_REQUIRED`
- `CONFIDENCE_REQUIRED`
- `SOURCE_STALE`
- `SOURCE_INVALIDATED`
- `SOURCE_TENANT_MISMATCH`
- `SOURCE_LEARNER_MISMATCH`
- `CONTRADICTORY_EVIDENCE`

Publication now evaluates provenance readiness before publishing. Blocked provenance prevents publication and preserves the prior current version.

## Contradictions and post-publication change

Contradictory evidence is preserved as a first-class link. It does not overwrite an attribute. Contradictions mark the attribute for review and may move the profile to `NEEDS_REVIEW`.

When evidence is later withdrawn, invalidated, stale, or superseded, the published profile version remains historically truthful. The platform can explain that the version was published when evidence was considered valid and that the evidence changed later.

## Non-goals

PI-7B.2 does not:

- implement frontend behavior;
- expose public APIs;
- automatically ingest onboarding, diagnostic, assessment, mastery, or learning-session evidence;
- copy raw evidence;
- form observed identity;
- form derived guidance;
- aggregate confidence;
- infer learner traits;
- create review workflows or dashboards.

## Manual validation

```powershell
docker compose exec backend pytest apps/learning_identity
docker compose exec backend pytest apps/learning_identity/tests/test_evidence_registry.py
docker compose exec backend pytest apps/learning_identity/tests/test_evidence_services.py
docker compose exec backend pytest apps/learning_identity/tests/test_provenance_publication.py
docker compose exec backend pytest apps/learning_identity/tests/test_provenance_queries.py
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py migrate
.\scripts\validate_backend.ps1
```
