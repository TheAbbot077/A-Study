# Teaching-Readiness Governance (PI-6D.5)

Status: implemented, awaiting manual Docker and pytest validation.

PI-6D.5 establishes `EvaluateTeachingReadinessService` as the sole backend authority permitted to transition a `ContentProcessingJob` to `READY_FOR_TEACHING`.

## Constitutional gate

The governed sequence is:

`durable source → processing evidence → human review → approval → immutable projection → controlled population → approved retrieval synchronization → teaching-readiness evaluation → READY_FOR_TEACHING`

`SYNCHRONIZED` does not mean `READY_FOR_TEACHING`. Progress reaching 100, proposal approval, population completion, legacy indexing, serializers, views, tasks, and admin cannot independently grant readiness.

`ContentProcessingJob.status` remains authoritative. `LearningResource.status` continues to represent its separate draft/active/archive lifecycle; no duplicate readiness boolean or independently editable resource state was added.

## Snapshot and policy

The cross-context snapshot adapter reconciles immutable identifiers and safe evidence from Storage, Content Processing, Academic Review, Academic, and Retrieval. Application and policy code do not import foreign ORM models.

`TeachingReadinessSnapshot` is immutable. Its SHA-256 lineage fingerprint covers the complete normalized snapshot and `teaching-readiness-v1` policy version. The deterministic policy performs no queries, writes, events, provider calls, or LLM work.

Ordered blocker checks cover:

- durable source existence and availability;
- current successful processing attempt and extraction/structure/segmentation outputs;
- blocking processing diagnostics;
- completed human review and resolved findings;
- authorized approval and populated immutable projection;
- population fingerprints, mapping reconciliation, and substantive active Academic content;
- synchronized retrieval, active generation, index/count reconciliation, and zero failed chunks;
- unique, non-orphaned chunks and 100% citation coverage;
- current policy version.

A valid evaluation with failed checks is persisted as `BLOCKED`; blockers are not application exceptions.

## Finalization, replay, and invalidation

Evaluation performs cheap idempotency checks before snapshot work. A request key is bound to its material request fingerprint, and equivalent lineage/policy evaluations replay without duplicate events.

Finalization locks the authoritative processing job, reassembles the snapshot, and compares lineage before persistence. Only a `READY` decision invokes the guarded job transition. Events and audit creation are scheduled after commit.

When a new evaluation observes changed authoritative lineage, the prior current evaluation is invalidated and readiness is revoked before the new decision is applied. `InvalidateTeachingReadinessService` provides the explicit idempotent invalidation boundary for source deletion/replacement, reprocessing, projection supersession, Academic replacement, retrieval-generation replacement, or withdrawal integrations. Historical evaluation evidence is retained.

## Closed legacy bypasses

- Legacy retrieval indexing now terminates at `READY_FOR_REVIEW`.
- The stage orchestrator no longer promotes an indexing result directly to `READY_FOR_TEACHING`.
- `MarkContentReadyForTeachingService` rejects direct use and redirects callers to the evaluator contract.
- The domain grant requires a persisted evaluation identifier and is called only by the evaluator.

## Backend APIs

- `GET /api/academic/learning-resources/{id}/teaching-readiness/`
- `POST /api/academic/learning-resources/{id}/teaching-readiness/evaluate/`
- `GET /api/content-processing/teaching-readiness/evaluations/{id}/`

The POST accepts an idempotency key, optional expected lineage fingerprint, and optional reason. It never accepts a decision, status, check, severity, threshold, or `ready` flag.

Frontend implementation is explicitly deferred.

## Manual validation

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend pytest apps/content_processing/tests/test_teaching_readiness_governance.py
docker compose exec backend pytest apps/content_processing/tests apps/academic_review/tests apps/retrieval/tests
```
