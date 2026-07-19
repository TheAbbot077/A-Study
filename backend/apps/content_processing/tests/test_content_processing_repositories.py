from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.content_processing.infrastructure.persistence.repositories import (
    DjangoContentProcessingJobRepository,
)
from apps.content_processing.models import ContentProcessingJob


class ContentProcessingJobRepositoryTests(SimpleTestCase):
    def test_get_for_update_locks_only_the_job_row_when_relations_are_nullable(self):
        locking_queryset = Mock()
        related_queryset = Mock()
        expected_job = Mock()
        locking_queryset.select_related.return_value = related_queryset
        related_queryset.get.return_value = expected_job

        with patch.object(
            ContentProcessingJob.objects,
            "select_for_update",
            return_value=locking_queryset,
        ) as select_for_update:
            result = DjangoContentProcessingJobRepository().get_for_update("job-1")

        self.assertIs(result, expected_job)
        select_for_update.assert_called_once_with(of=("self",))
        locking_queryset.select_related.assert_called_once_with(
            "resource",
            "stored_file",
            "legacy_import_job",
        )
        related_queryset.get.assert_called_once_with(id="job-1")
