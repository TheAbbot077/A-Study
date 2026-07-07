from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


Metadata = dict[str, Any]


def _validate_sequence_number(sequence_number: int, label: str) -> None:
    if sequence_number < 1:
        raise ValueError(f"{label} sequence_number must be greater than or equal to 1")


def _validate_unique_sequence_numbers(items: list[Any], label: str) -> None:
    seen: set[int] = set()
    duplicates: set[int] = set()

    for item in items:
        sequence_number = item.sequence_number
        if sequence_number in seen:
            duplicates.add(sequence_number)
        seen.add(sequence_number)

    if duplicates:
        duplicate_list = ", ".join(str(number) for number in sorted(duplicates))
        raise ValueError(f"{label} sequence_number values must be unique: {duplicate_list}")


@dataclass(frozen=True)
class ImportedConcept:
    title: str
    description: str = ""
    learning_objective: str = ""
    sequence_number: int = 1
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_sequence_number(self.sequence_number, "concept")


@dataclass(frozen=True)
class ImportedSection:
    title: str
    description: str = ""
    sequence_number: int = 1
    metadata: Metadata = field(default_factory=dict)
    concepts: list[ImportedConcept] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_sequence_number(self.sequence_number, "section")
        _validate_unique_sequence_numbers(self.concepts, "concept")


@dataclass(frozen=True)
class ContentImportResult:
    success: bool
    sections: list[ImportedSection] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.success:
            _validate_unique_sequence_numbers(self.sections, "section")

    @classmethod
    def succeeded(
        cls,
        sections: list[ImportedSection],
        warnings: list[str] | None = None,
        metadata: Metadata | None = None,
    ) -> "ContentImportResult":
        return cls(
            success=True,
            sections=sections,
            warnings=warnings or [],
            errors=[],
            metadata=metadata or {},
        )

    @classmethod
    def failed(
        cls,
        errors: list[str],
        warnings: list[str] | None = None,
        metadata: Metadata | None = None,
    ) -> "ContentImportResult":
        return cls(
            success=False,
            sections=[],
            warnings=warnings or [],
            errors=errors,
            metadata=metadata or {},
        )


class ContentImporter(ABC):
    @abstractmethod
    def can_import(self, source: Any) -> bool:
        raise NotImplementedError

    @abstractmethod
    def import_content(self, source: Any, context: Metadata | None = None) -> ContentImportResult:
        raise NotImplementedError
