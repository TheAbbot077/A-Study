from __future__ import annotations

from typing import Protocol, Sequence


class AcademicProposalEngine(Protocol):
    name: str
    version: str
    configuration_version: str
    def supports(self, hierarchy, segmentation) -> bool: ...
    def generate(self, hierarchy, nodes: Sequence[object], segments: Sequence[object]): ...
