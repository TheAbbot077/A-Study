from types import SimpleNamespace
from unittest.mock import Mock

from apps.content_processing.application.services import ProcessingStageContext
from apps.content_processing.application.stage_processors import BuildSemanticSegmentsProcessor, ReconstructDocumentHierarchyProcessor
from apps.content_processing.domain.models import ProcessingStage


def context(stage):
    return ProcessingStageContext("job", "attempt", "resource", "file", "pipeline", stage, "correlation")


def test_structuring_processor_returns_durable_hierarchy_references():
    hierarchy = SimpleNamespace(id="hierarchy", root_node_id="root", result_checksum="checksum")
    service = Mock(); service.execute.return_value = (hierarchy, [SimpleNamespace()], [])
    result = ReconstructDocumentHierarchyProcessor(service).execute(context(ProcessingStage.STRUCTURING))
    assert result.next_stage == ProcessingStage.SEGMENTING
    assert result.output_references == {"document_hierarchy_id": "hierarchy", "root_node_id": "root", "node_count": 1}


def test_segmenting_processor_returns_durable_segmentation_references():
    segmentation = SimpleNamespace(id="segmentation", result_checksum="checksum")
    service = Mock(); service.execute.return_value = (segmentation, [SimpleNamespace(), SimpleNamespace()], [])
    result = BuildSemanticSegmentsProcessor(service).execute(context(ProcessingStage.SEGMENTING))
    assert result.next_stage == ProcessingStage.VALIDATING
    assert result.output_references == {"document_segmentation_id": "segmentation", "segment_count": 2}
