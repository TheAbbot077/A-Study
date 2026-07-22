# PI-6F.5 Evidence-to-Curriculum Mapping and Coverage

PI-6F.5 maps immutable extraction evidence to an immutable published curriculum graph and determines material coverage. The graph controls what must be learned; PI-6F.4 controls learner placement; PI-6F.5 controls only which existing materials support graph nodes. Coverage never means learner knowledge, mastery, teaching readiness, or a grade.

## Frozen authority

Each run freezes tenant, intent, published graph fingerprint, ordered resource/stored-file/job/extraction identities, source dispositions, and all algorithm and policy versions. Canonical manifests provide idempotency. Source, extraction, graph, or policy changes require successor state; historical evidence, candidates, decisions, findings, and evaluations are retained.

Evidence units reuse completed `DocumentExtraction` blocks and preserve resource, file, processing job, extraction, block, page, checksums, language, licence, safety, and citation snapshots. Exact normalized duplicates share a deterministic cluster but remain separate provenance records. Headings are retained as context but cannot establish substantive coverage.

## Candidate versus decision

Bounded lexical candidates are advisory, versioned, and deterministically ranked. Existing embeddings are not used as authority; semantic unavailability is explicit. Hard safety, licence, provenance, substantive-content, and node-type rules execute before score thresholds. A top-ranked candidate may be rejected or proposed for review. Only current `ACCEPTED` mappings contribute positively.

## Coverage and gap handoff

Every graph node receives one of `UNEVALUATED`, `COVERED`, `PARTIAL`, `MISSING`, `CONFLICTING`, `OUT_OF_SCOPE`, `SUPPLEMENTARY`, or `NOT_APPLICABLE`. Conflicts take precedence. Duplicate sources do not inflate corroboration. Organizational graph nodes are not applicable; applicable nodes fail closed when material is absent. Findings use stable codes and structured details.

Only a completed, current evaluation exposes its fingerprinted gap set to PI-6F.6. Stale or invalidated evaluations are not returned as current. PI-6F.5 does not acquire resources, alter the graph, build a bridge, synchronize retrieval, or declare teaching readiness.

## Orchestration

Workers receive only run identifiers and execute bounded stages: `self_study.build_content_evidence`, `self_study.generate_evidence_mapping_candidates`, and `self_study.evaluate_curriculum_coverage`. State commits before follow-up dispatch and events contain identifiers and bounded counts only.
