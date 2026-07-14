from __future__ import annotations

from typing import Protocol, Sequence


class DocumentHierarchyReconstructor(Protocol):
    def reconstruct(self, blocks: Sequence[object]): ...


class SemanticSegmenter(Protocol):
    def classify(self, blocks: Sequence[object], node: object): ...
    def groups(self, relationships: Sequence[object]): ...


class SegmentSemanticClassifier(Protocol):
    def classify(self, candidate: object, context: object): ...
