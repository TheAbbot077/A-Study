from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.content_intelligence.infrastructure.persistence.repositories import (
    DjangoContentImportJobRepository,
    DjangoParsedDocumentRepository,
    DjangoParserPipelineRunRepository,
)
from apps.content_intelligence.models import ContentImportJob, ParsedConceptCandidate, ParsedDocument, ParsedSection, ParserPipelineRun


class ContentIntelligenceRepositoryTests(SimpleTestCase):
    def test_import_job_repository_lists_all(self):
        repository = DjangoContentImportJobRepository()
        expected = [Mock(spec=ContentImportJob)]

        with patch("apps.content_intelligence.infrastructure.persistence.repositories.ContentImportJob.objects") as job_objects:
            job_objects.select_related.return_value.order_by.return_value = expected
            jobs = repository.list_all()

        self.assertEqual(jobs, expected)

    def test_parsed_document_repository_replaces_sections_and_concepts(self):
        repository = DjangoParsedDocumentRepository()
        parsed_document = Mock(spec=ParsedDocument)
        section = Mock(spec=ParsedSection)
        section.save = Mock()
        concept = Mock(spec=ParsedConceptCandidate)
        concept.save = Mock()

        with patch("apps.content_intelligence.infrastructure.persistence.repositories.ParsedSection.objects") as section_objects:
            repository.replace_sections(parsed_document, [section])
            section_objects.filter.assert_called_once_with(parsed_document=parsed_document)
            section.save.assert_called_once()

        with patch("apps.content_intelligence.infrastructure.persistence.repositories.ParsedConceptCandidate.objects") as concept_objects:
            repository.replace_concepts(section, [concept])
            concept_objects.filter.assert_called_once_with(parsed_section=section)
            concept.save.assert_called_once()

    def test_pipeline_run_repository_lists_for_job(self):
        repository = DjangoParserPipelineRunRepository()
        job = Mock(spec=ContentImportJob)
        expected = [Mock(spec=ParserPipelineRun)]

        with patch("apps.content_intelligence.infrastructure.persistence.repositories.ParserPipelineRun.objects") as run_objects:
            run_objects.filter.return_value.order_by.return_value = expected
            runs = repository.list_for_job(job)

        self.assertEqual(runs, expected)
