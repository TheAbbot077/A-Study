from __future__ import annotations

from typing import Any

from apps.academic.importers.contracts import (
    ContentImporter,
    ContentImportResult,
    ImportedConcept,
    ImportedSection,
    Metadata,
)


class ManualContentImporter(ContentImporter):
    def can_import(self, source: Any) -> bool:
        return isinstance(source, dict) and isinstance(source.get("sections"), list)

    def import_content(self, source: Any, context: Metadata | None = None) -> ContentImportResult:
        if not self.can_import(source):
            return ContentImportResult.failed(["Manual import source must be a mapping with a sections list"])

        try:
            sections = [
                ImportedSection(
                    title=section["title"],
                    description=section.get("description", ""),
                    sequence_number=section.get("sequence_number", 1),
                    metadata=section.get("metadata", {}),
                    concepts=[
                        ImportedConcept(
                            title=concept["title"],
                            description=concept.get("description", ""),
                            learning_objective=concept.get("learning_objective", ""),
                            sequence_number=concept.get("sequence_number", 1),
                            metadata=concept.get("metadata", {}),
                        )
                        for concept in section.get("concepts", [])
                    ],
                )
                for section in source["sections"]
            ]
            return ContentImportResult.succeeded(
                sections=sections,
                warnings=source.get("warnings", []),
                metadata={
                    **source.get("metadata", {}),
                    **(context or {}),
                    "importer": self.__class__.__name__,
                },
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            return ContentImportResult.failed([str(exc)])
