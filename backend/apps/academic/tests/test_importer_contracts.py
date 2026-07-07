from unittest import TestCase

from apps.academic.importers import (
    ContentImporter,
    ContentImportResult,
    ImportedConcept,
    ImportedSection,
    ManualContentImporter,
)


class DummyImporter(ContentImporter):
    def can_import(self, source):
        return source == "supported"

    def import_content(self, source, context=None):
        if not self.can_import(source):
            return ContentImportResult.failed(["unsupported source"])
        return ContentImportResult.succeeded(
            sections=[
                ImportedSection(
                    title="Section 1",
                    sequence_number=1,
                    concepts=[ImportedConcept(title="Concept 1", sequence_number=1)],
                )
            ],
            metadata=context or {},
        )


class ImporterContractTests(TestCase):
    def test_importer_contract_can_be_subclassed(self):
        importer = DummyImporter()

        self.assertTrue(importer.can_import("supported"))
        self.assertFalse(importer.can_import("unsupported"))

    def test_successful_import_result(self):
        result = ContentImportResult.succeeded(
            sections=[ImportedSection(title="Section 1", sequence_number=1)],
            warnings=["review recommended"],
            metadata={"source": "manual"},
        )

        self.assertTrue(result.success)
        self.assertEqual(len(result.sections), 1)
        self.assertEqual(result.warnings, ["review recommended"])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.metadata, {"source": "manual"})

    def test_failed_import_result_preserves_errors(self):
        result = ContentImportResult.failed(["missing title"], metadata={"source": "manual"})

        self.assertFalse(result.success)
        self.assertEqual(result.sections, [])
        self.assertEqual(result.errors, ["missing title"])
        self.assertEqual(result.metadata, {"source": "manual"})

    def test_imported_section_structure(self):
        concept = ImportedConcept(title="Concept 1", sequence_number=1)
        section = ImportedSection(
            title="Section 1",
            description="Introductory section",
            sequence_number=1,
            metadata={"page": 1},
            concepts=[concept],
        )

        self.assertEqual(section.title, "Section 1")
        self.assertEqual(section.description, "Introductory section")
        self.assertEqual(section.sequence_number, 1)
        self.assertEqual(section.metadata, {"page": 1})
        self.assertEqual(section.concepts, [concept])

    def test_imported_concept_structure(self):
        concept = ImportedConcept(
            title="Opportunity Cost",
            description="Cost of the next best alternative",
            learning_objective="Explain opportunity cost",
            sequence_number=1,
            metadata={"difficulty": "introductory"},
        )

        self.assertEqual(concept.title, "Opportunity Cost")
        self.assertEqual(concept.description, "Cost of the next best alternative")
        self.assertEqual(concept.learning_objective, "Explain opportunity cost")
        self.assertEqual(concept.sequence_number, 1)
        self.assertEqual(concept.metadata, {"difficulty": "introductory"})

    def test_validation_rejects_section_sequence_number_below_one(self):
        with self.assertRaises(ValueError):
            ImportedSection(title="Invalid", sequence_number=0)

    def test_validation_rejects_duplicate_section_sequence_numbers(self):
        with self.assertRaises(ValueError):
            ContentImportResult.succeeded(
                sections=[
                    ImportedSection(title="Section 1", sequence_number=1),
                    ImportedSection(title="Section 2", sequence_number=1),
                ]
            )

    def test_validation_rejects_concept_sequence_number_below_one(self):
        with self.assertRaises(ValueError):
            ImportedConcept(title="Invalid", sequence_number=0)

    def test_validation_rejects_duplicate_concept_sequence_numbers_within_section(self):
        with self.assertRaises(ValueError):
            ImportedSection(
                title="Section 1",
                sequence_number=1,
                concepts=[
                    ImportedConcept(title="Concept 1", sequence_number=1),
                    ImportedConcept(title="Concept 2", sequence_number=1),
                ],
            )

    def test_manual_importer_transforms_structured_input(self):
        importer = ManualContentImporter()
        source = {
            "metadata": {"source_label": "manual outline"},
            "sections": [
                {
                    "title": "Section 1",
                    "description": "Opening section",
                    "sequence_number": 1,
                    "metadata": {"page": 1},
                    "concepts": [
                        {
                            "title": "Concept 1",
                            "description": "First concept",
                            "learning_objective": "Describe the first concept",
                            "sequence_number": 1,
                            "metadata": {"confidence": "human-authored"},
                        }
                    ],
                }
            ],
        }

        result = importer.import_content(source, context={"requested_by": "academic-admin"})

        self.assertTrue(result.success)
        self.assertEqual(result.sections[0].title, "Section 1")
        self.assertEqual(result.sections[0].concepts[0].title, "Concept 1")
        self.assertEqual(result.metadata["source_label"], "manual outline")
        self.assertEqual(result.metadata["requested_by"], "academic-admin")
        self.assertEqual(result.metadata["importer"], "ManualContentImporter")
