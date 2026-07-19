from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError

from apps.retrieval.application.synchronization_services import (
    BuildRetrievalSynchronizationManifestService,
    EvaluateRetrievalSynchronizationReadinessService,
)
from apps.retrieval.domain.synchronization import CitationSpecification
from apps.retrieval.infrastructure.synchronization_gateway import AcademicUnit, PopulationSnapshot
from apps.retrieval.models import RetrievalSynchronizationRun


def snapshot(**changes):
    values = {
        "population_run_id": "population-1", "projection_id": "projection-1",
        "processing_job_id": "processing-1", "resource_id": "resource-1",
        "subject_id": "subject-1", "institution_id": "institution-1",
        "source_fingerprint": "source-1", "projection_fingerprint": "source-1",
        "status": "populated", "projection_status": "populated",
        "expected_sections": 1, "expected_concepts": 1,
        "mapped_sections": 1, "mapped_concepts": 1,
        "units": (AcademicUnit(
            "section-1", "section-key", "Foundations", 1,
            "concept-1", "concept-key", "Cells", 1,
            "Cells are the basic structural units of life.", "segment-1", 3, 4,
        ),),
    }
    values.update(changes)
    return PopulationSnapshot(**values)


class TestCitationSpecification:
    def test_missing_page_is_rejected(self):
        with pytest.raises(ValueError, match="CITATION_PROVENANCE_MISSING"):
            CitationSpecification(0, 0, "segment", "source", "label")


class TestSynchronizationRunLifecycle:
    def test_complete_requires_full_reconciliation(self):
        run = RetrievalSynchronizationRun(
            status=RetrievalSynchronizationRun.Status.SYNCHRONIZING,
            planned_chunk_count=2, indexed_chunk_count=1,
            keyword_indexed_count=1, vector_indexed_count=1, citation_coverage=1,
        )
        with pytest.raises(ValidationError, match="INDEX_RECONCILIATION_FAILED"):
            run.complete()

    def test_terminal_run_cannot_fail(self):
        run = RetrievalSynchronizationRun(status=RetrievalSynchronizationRun.Status.SYNCHRONIZED)
        with pytest.raises(ValidationError, match="immutable"):
            run.fail("SYNCHRONIZATION_FAILED")


class TestReadiness:
    def test_incomplete_mappings_and_provenance_block(self, monkeypatch):
        gateway = Mock()
        gateway.load.return_value = snapshot(
            expected_sections=2, mapped_sections=1,
            units=(AcademicUnit(
                "section-1", "key", "Section", 1, "concept-1", "concept", "Concept", 1,
                "Official Academic text", "segment-1", 0, 0,
            ),),
        )
        monkeypatch.setattr("apps.retrieval.application.synchronization_services.RetrievalGeneration.objects", Mock())
        monkeypatch.setattr("apps.retrieval.application.synchronization_services.RetrievalSynchronizationRun.objects", Mock())
        service = EvaluateRetrievalSynchronizationReadinessService(gateway=gateway)

        result = service.evaluate("population-1")

        assert not result.ready
        assert "SECTION_MAPPINGS_INCOMPLETE" in result.blockers
        assert "CITATION_PROVENANCE_MISSING" in result.blockers


class TestManifest:
    def test_manifest_and_chunk_keys_are_deterministic(self):
        gateway = Mock()
        gateway.load.return_value = snapshot()
        service = BuildRetrievalSynchronizationManifestService(gateway=gateway)

        first = service.build("population-1")
        second = service.build("population-1")

        assert first == second
        assert first.chunks[0].stable_key == second.chunks[0].stable_key
        assert first.chunks[0].text == "Cells are the basic structural units of life."

    def test_official_empty_content_is_not_replaced_by_projection_text(self):
        gateway = Mock()
        gateway.load.return_value = snapshot(units=(AcademicUnit(
            "section-1", "key", "Section", 1, "concept-1", "concept", "Concept", 1,
            "", "segment-1", 1, 1,
        ),))

        with pytest.raises(ValidationError, match="NO_RETRIEVABLE_CONTENT"):
            BuildRetrievalSynchronizationManifestService(gateway=gateway).build("population-1")
