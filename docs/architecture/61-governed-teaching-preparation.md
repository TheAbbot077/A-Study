# PI-6F.7 Governed Teaching Preparation and Learning-Resource Assembly

PI-6F.7 turns an active PI-6F.6 bridge plan into a governed teaching-preparation authority. It assembles citation-backed node teaching packs from accepted PI-6F.5 evidence mappings, publishes a bounded self-study retrieval manifest, verifies exact publication identity, and evaluates readiness for downstream teaching orchestration.

It does not generate lesson text, infer learner mastery, create assessments, rerun diagnostics, remap evidence, mutate the curriculum graph, or begin teaching.

## Authoritative Inputs

- Active `BridgePlan` and immutable `BridgePlanNode` ordering from PI-6F.6.
- Published curriculum graph version and graph fingerprint from PI-6F.3.
- Current diagnostic and coverage fingerprints frozen through the bridge plan.
- Completed PI-6F.5 coverage evaluation, mapping-set fingerprint, accepted evidence mappings, evidence units, citations, resource provenance, license disposition, safety disposition, and duplicate clusters.

All command fingerprints exclude timestamps, task IDs, and volatile publication timing.

## Lifecycle

`TeachingPreparationRun` tracks asynchronous assembly:

- `PENDING`
- `ASSEMBLING`
- `ASSEMBLY_READY`
- `PUBLISHING`
- `EVALUATING_READINESS`
- `COMPLETED`
- `FAILED`
- `STALE`
- `INVALIDATED`
- `SUPERSEDED`

`TeachingPreparationManifest` is the governed preparation authority:

- `PROPOSED`
- `READY_FOR_REVIEW`
- `APPROVED`
- `PUBLISHING`
- `PUBLISHED`
- `READY`
- `BLOCKED`
- `REJECTED`
- `STALE`
- `INVALIDATED`
- `SUPERSEDED`

Approval, publication, verification, and readiness are separate operations. A blocked manifest may be approved as a governance record only if policy permits, but it cannot be published as executable teaching authority.

## Teaching Packs

Each `NodeTeachingPack` mirrors one bridge-plan node and retains:

- bridge disposition;
- material feasibility;
- coverage state;
- topological layer and ordinal;
- role-policy snapshot;
- assignment counts;
- source-diversity and duplicate-cluster counts;
- blocker counts;
- immutable pack fingerprint.

Each `TeachingPackResource` binds one accepted PI-6F.5 mapping to a role such as `PRIMARY_EXPLANATION`, `PREREQUISITE_SUPPORT`, `DEFINITION`, `WORKED_EXAMPLE`, `PROCEDURE`, `PRACTICE`, `ASSESSMENT_SUPPORT`, `REFERENCE`, `ENRICHMENT`, or `CONFLICT_WARNING`.

Conflict warnings retain provenance but cannot satisfy ordinary explanation roles.

## Eligibility and Selection

Eligibility requires tenant and graph scope through the active bridge plan, accepted/current PI-6F.5 mappings, current resource revision, extraction provenance, citation snapshot, license disposition, safety disposition, and role compatibility.

Hard blockers are persisted as `TeachingReadinessFinding` records. The assembly does not silently omit a required blocker if omission would misrepresent readiness.

Role classification is deterministic and uses PI-6F.5 mapping class, evidence type, graph-node type, bridge prerequisite disposition, citation, duplicate cluster, and source identity. Semantic rank is not an authority.

## Retrieval Publication

PI-6F.7 reuses the platform retrieval boundary by publishing a self-study teaching retrieval manifest rather than creating a second search system. The manifest authoritatively lists the exact permitted `TeachingPackResource` assignment identities and metadata filters:

- tenant;
- preparation manifest;
- bridge plan;
- graph version;
- assignment IDs;
- role exclusions;
- retrieval schema version.

Publication verification compares expected and published assignment identities, counts, schema version, and manifest fingerprint. Task completion alone is not readiness.

## Readiness

Readiness is deterministic and fail-closed.

Node readiness requires current plan node authority, sufficient coverage, mandatory role satisfaction, source diversity, eligible selected resources, complete citations, verified retrieval publication, and no unresolved blocker.

Plan readiness requires all mandatory packs to be ready. Optional reinforcement cannot compensate for blocked mandatory nodes. Readiness is not learner mastery.

## Staleness

Teaching preparations become stale when bridge plans, graphs, coverage, mappings, source retirement, retrieval publication, policy, or algorithm authority changes. Historical manifests remain immutable; downstream handoff rejects stale or unverified authorities.

## APIs

The self-study API exposes:

- `GET/POST /api/self-study/teaching-preparation-runs/`
- `GET /api/self-study/teaching-preparation-runs/{run_id}/`
- `GET /api/self-study/teaching-preparation-runs/{run_id}/manifest/`
- `GET /api/self-study/teaching-preparations/`
- `GET /api/self-study/teaching-preparations/{manifest_id}/`
- `GET /api/self-study/teaching-preparations/{manifest_id}/node-packs/`
- `GET /api/self-study/teaching-preparations/{manifest_id}/selected-resources/`
- `GET /api/self-study/teaching-preparations/{manifest_id}/findings/`
- `GET /api/self-study/teaching-preparations/{manifest_id}/publication/`
- `GET /api/self-study/teaching-preparations/{manifest_id}/readiness/`
- `POST /api/self-study/teaching-preparations/{manifest_id}/approve/`
- `POST /api/self-study/teaching-preparations/{manifest_id}/reject/`
- `POST /api/self-study/teaching-preparations/{manifest_id}/publish/`
- `POST /api/self-study/teaching-preparations/{manifest_id}/invalidate/`
- `POST /api/self-study/teaching-preparations/{manifest_id}/recalculate/`
- `GET /api/self-study/teaching-preparations/current-handoff/{intent_id}/`

Query endpoints are tenant scoped and paginated. Command endpoints use expected versions where lifecycle mutation is possible.

## Workers and Events

Identifier-only tasks:

- `self_study.assemble_teaching_preparation`
- `self_study.publish_teaching_retrieval`
- `self_study.evaluate_teaching_readiness`

Events:

- `self_study.teaching_preparation_run.created`
- `self_study.teaching_preparation_manifest.generated`
- `self_study.teaching_preparation_manifest.blocked`
- `self_study.teaching_preparation.approved`
- `self_study.teaching_preparation.rejected`
- `self_study.teaching_retrieval.publication_requested`
- `self_study.teaching_retrieval.verified`
- `self_study.teaching_readiness.evaluated`
- `self_study.teaching_preparation.ready`
- `self_study.teaching_preparation.blocked`
- `self_study.teaching_preparation.stale`
- `self_study.teaching_preparation.invalidated`
- `self_study.teaching_preparation.failed`

Events carry identifiers and bounded summaries only.

## Manual Validation

Run validation in Docker after review. This implementation was not validated during creation.
