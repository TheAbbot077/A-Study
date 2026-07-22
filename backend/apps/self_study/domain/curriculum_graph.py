from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from ..graph_models import CitationType, EdgeType, NodeType, RequirementType

BUILDER_ALGORITHM_VERSION = "pi-6f.3-structured-v1"
VALIDATION_ALGORITHM_VERSION = "pi-6f.3-validation-v1"
STABLE_KEY_ALGORITHM_VERSION = "pi-6f.3-stable-key-v1"


def _canonical_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def stable_node_key(*, source_version_id: str, authority_namespace: str, external_identifier: str, node_type: str, structural_path: str, title: str) -> str:
    return _digest({
        "algorithm": STABLE_KEY_ALGORITHM_VERSION,
        "source": source_version_id,
        "namespace": _canonical_text(authority_namespace),
        "external_identifier": _canonical_text(external_identifier),
        "node_type": node_type,
        "path": _canonical_text(structural_path),
        "title": _canonical_text(title),
    })


def stable_edge_key(*, edge_type: str, source_key: str, target_key: str, requirement: str) -> str:
    symmetric = edge_type in {EdgeType.EQUIVALENT_TO, EdgeType.CONFLICTS_WITH}
    endpoints = sorted([source_key, target_key]) if symmetric else [source_key, target_key]
    return _digest({
        "algorithm": STABLE_KEY_ALGORITHM_VERSION,
        "edge_type": edge_type,
        "endpoints": endpoints,
        "requirement": requirement,
    })


@dataclass(frozen=True)
class GraphNodeSpecification:
    local_key: str
    node_type: str
    title: str
    description: str
    ordinal: int
    depth: int
    source_curriculum_version_id: str
    authority_namespace: str
    external_identifier: str
    structural_path: str
    external_prerequisite_status: str
    metadata: dict


@dataclass(frozen=True)
class GraphEdgeSpecification:
    local_key: str
    edge_type: str
    source_local_key: str
    target_local_key: str
    ordinal: int
    requirement: str
    strength: Decimal
    source_curriculum_version_id: str
    derivation: str
    metadata: dict


@dataclass(frozen=True)
class GraphCitationSpecification:
    target_kind: str
    target_local_key: str
    curriculum_version_id: str
    source_document_id: str
    source_uri: str
    source_locator: dict
    normalized_excerpt: str
    source_language: str
    citation_type: str
    confidence: Decimal
    rationale: str


@dataclass(frozen=True)
class CurriculumGraphSpecification:
    construction_method: str
    producer: str
    nodes: tuple[GraphNodeSpecification, ...]
    edges: tuple[GraphEdgeSpecification, ...]
    citations: tuple[GraphCitationSpecification, ...]

    @classmethod
    def from_payload(cls, payload: dict) -> "CurriculumGraphSpecification":
        if not isinstance(payload, dict):
            raise ValueError("Specification must be an object.")
        try:
            nodes = tuple(GraphNodeSpecification(
                local_key=str(item["local_key"]), node_type=str(item["node_type"]), title=str(item["title"]),
                description=str(item.get("description", "")), ordinal=int(item["ordinal"]), depth=int(item.get("depth", 0)),
                source_curriculum_version_id=str(item["source_curriculum_version_id"]), authority_namespace=str(item["authority_namespace"]),
                external_identifier=str(item.get("external_identifier", "")), structural_path=str(item["structural_path"]),
                external_prerequisite_status=str(item.get("external_prerequisite_status", "")), metadata=dict(item.get("metadata", {})),
            ) for item in payload.get("nodes", []))
            edges = tuple(GraphEdgeSpecification(
                local_key=str(item["local_key"]), edge_type=str(item["edge_type"]), source_local_key=str(item["source_local_key"]),
                target_local_key=str(item["target_local_key"]), ordinal=int(item["ordinal"]), requirement=str(item.get("requirement", "")),
                strength=Decimal(str(item.get("strength", 1))), source_curriculum_version_id=str(item["source_curriculum_version_id"]),
                derivation=str(item.get("derivation", "")), metadata=dict(item.get("metadata", {})),
            ) for item in payload.get("edges", []))
            citations = tuple(GraphCitationSpecification(
                target_kind=str(item["target_kind"]), target_local_key=str(item["target_local_key"]),
                curriculum_version_id=str(item["curriculum_version_id"]), source_document_id=str(item.get("source_document_id", "")),
                source_uri=str(item["source_uri"]), source_locator=dict(item["source_locator"]), normalized_excerpt=str(item.get("normalized_excerpt", "")),
                source_language=str(item["source_language"]), citation_type=str(item["citation_type"]),
                confidence=Decimal(str(item.get("confidence", 1))), rationale=str(item.get("rationale", "")),
            ) for item in payload.get("citations", []))
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise ValueError("Specification shape is invalid.") from exc
        return cls(str(payload.get("construction_method", "")), str(payload.get("producer", "")), nodes, edges, citations)

    def validate_shape(self, allowed_source_versions: set[str]) -> None:
        if self.construction_method not in {"STRUCTURED_IMPORT", "CURATED_AUTHORING", "COMPOSITE_ASSEMBLY"}:
            raise ValueError("Construction method is not permitted.")
        if not self.producer.strip() or not self.nodes:
            raise ValueError("Producer and nodes are required.")
        local_keys = [node.local_key for node in self.nodes]
        if len(local_keys) != len(set(local_keys)):
            raise ValueError("Node local keys collide.")
        edge_keys = [edge.local_key for edge in self.edges]
        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("Edge local keys collide.")
        local_set = set(local_keys)
        for node in self.nodes:
            if node.node_type not in NodeType.values or not node.title.strip() or node.ordinal < 1 or node.depth < 0:
                raise ValueError("Node specification is invalid.")
            if node.source_curriculum_version_id not in allowed_source_versions:
                raise ValueError("Node source is outside the authoritative selection.")
        for edge in self.edges:
            if edge.edge_type not in EdgeType.values or edge.source_local_key not in local_set or edge.target_local_key not in local_set:
                raise ValueError("Edge specification is invalid.")
            if edge.source_local_key == edge.target_local_key:
                raise ValueError("Self edges are prohibited.")
            if edge.edge_type == EdgeType.REQUIRES and edge.requirement not in RequirementType.values:
                raise ValueError("Prerequisite requirement is invalid.")
            if edge.edge_type != EdgeType.REQUIRES and edge.requirement:
                raise ValueError("Requirement applies only to prerequisite edges.")
            if edge.source_curriculum_version_id not in allowed_source_versions or not Decimal("0") <= edge.strength <= Decimal("1"):
                raise ValueError("Edge source or strength is invalid.")
        targets = {(item.target_kind, item.target_local_key) for item in self.citations}
        for citation in self.citations:
            valid_target = (citation.target_kind == "NODE" and citation.target_local_key in local_set) or (citation.target_kind == "EDGE" and citation.target_local_key in set(edge_keys))
            if not valid_target or citation.curriculum_version_id not in allowed_source_versions:
                raise ValueError("Citation target or source is invalid.")
            if citation.citation_type not in CitationType.values or not citation.source_uri or not citation.source_locator:
                raise ValueError("Citation is incomplete.")
        authoritative_nodes = {node.local_key for node in self.nodes}
        if any(("NODE", key) not in targets for key in authoritative_nodes):
            raise ValueError("Every authoritative node requires a citation.")


def graph_fingerprint(*, source_selection_fingerprint: str, component_version_ids: list[str], nodes: list[dict], edges: list[dict], citations: list[dict], construction_method: str) -> str:
    return _digest({
        "source_selection": source_selection_fingerprint,
        "components": sorted(component_version_ids),
        "nodes": sorted(nodes, key=lambda item: item["stable_key"]),
        "edges": sorted(edges, key=lambda item: item["stable_key"]),
        "citations": sorted(citations, key=lambda item: (item["target_key"], item["citation_type"], item["source_uri"], json.dumps(item["source_locator"], sort_keys=True))),
        "builder": BUILDER_ALGORITHM_VERSION,
        "stable_key": STABLE_KEY_ALGORITHM_VERSION,
        "construction_method": construction_method,
    })
