from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.content_intelligence.application.confidence_service import ConfidenceScoringService
from apps.content_intelligence.domain.exceptions import ImportLifecycleError
from apps.content_intelligence.domain.models import ContentExtractionResult, ContentImportJob, ParsedConceptCandidate, ParsedSection, ParserPipelineRun


class ContentIntelligenceDomainTests(SimpleTestCase):
    def test_import_job_lifecycle(self):
        job = ContentImportJob(learning_resource=self._resource(), format_type=ContentImportJob.FormatType.PDF)

        job.start()
        job.mark_ocr_requested()
        job.mark_ocr_completed()
        job.complete()

        self.assertEqual(job.status, ContentImportJob.Status.COMPLETED)
        self.assertTrue(job.ocr_requested)
        self.assertTrue(job.ocr_used)

    def test_cannot_cancel_completed_job(self):
        job = ContentImportJob(learning_resource=self._resource(), format_type=ContentImportJob.FormatType.DOCX, status=ContentImportJob.Status.COMPLETED)

        with self.assertRaises(ImportLifecycleError):
            job.cancel()

    def test_pipeline_run_lifecycle(self):
        run = ParserPipelineRun(import_job=ContentImportJob(learning_resource=self._resource(), format_type=ContentImportJob.FormatType.PDF))

        run.start("extraction")
        run.advance("validation")
        run.complete()

        self.assertEqual(run.status, ParserPipelineRun.Status.COMPLETED)
        self.assertEqual(run.current_stage, "validation")

    def test_confidence_scoring_is_deterministic(self):
        result = ContentExtractionResult(char_count=300, sufficient_text=True, ocr_used=False, page_count=4)
        sections = [ParsedSection(heading="Chapter 1", confidence=0.8, sequence_number=1), ParsedSection(heading="Chapter 2", confidence=0.6, sequence_number=2)]
        concepts = [ParsedConceptCandidate(title="Concept A", confidence=0.7, sequence_number=1), ParsedConceptCandidate(title="Concept B", confidence=0.9, sequence_number=2)]
        service = ConfidenceScoringService()

        self.assertEqual(service.score_extraction_quality(result), service.score_extraction_quality(result))
        self.assertEqual(service.score_section_confidence(sections), 0.7)
        self.assertEqual(service.score_concept_confidence(concepts), 0.8)

    def _resource(self):
        return SimpleNamespace(id="resource-1", title="Resource")
