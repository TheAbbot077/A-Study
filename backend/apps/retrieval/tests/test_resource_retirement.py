from unittest.mock import Mock, patch

import pytest

from apps.retrieval.application import IndexAcademicPopulationService, RetireRetrievalResourceService
from apps.retrieval.models import RetrievalReadiness


@pytest.mark.django_db
def test_resource_retirement_marks_collections_and_index_jobs_stale():
    collections = Mock()
    collections.values_list.return_value = ["collection-1"]
    collections.update.return_value = 1
    index_jobs = Mock()
    index_jobs.update.return_value = 1
    publisher = Mock()
    resource = Mock(id="resource-1")

    with patch("apps.retrieval.application.services.RetrievalChunkCollection.objects.filter", return_value=collections):
        with patch("apps.retrieval.application.services.RetrievalIndexJob.objects.filter", return_value=index_jobs):
            result = RetireRetrievalResourceService(event_publisher=publisher).retire(resource)

    assert result == {"collection_count": 1, "index_job_count": 1}
    assert collections.update.call_args.kwargs["readiness"] == RetrievalReadiness.STALE
    assert index_jobs.update.call_args.kwargs["status"] == RetrievalReadiness.STALE
    assert publisher.publish.call_args.args[0].event_name == "retrieval.resource_retired"


def test_deleted_processing_job_prevents_stale_index_advancement():
    population_job = Mock()
    population_job.job.status = "deleted"
    population_job.proposal.resource.status = "active"

    assert IndexAcademicPopulationService._resource_is_retired(population_job) is True
