import pytest
from apps.retrieval.models import RetrievalIndexJob, RetrievalReadiness


@pytest.mark.django_db
def test_index_job_requires_every_chunk_before_indexed():
    job = RetrievalIndexJob(chunk_count=2)
    with pytest.raises(Exception):
        job.complete(1, "checksum")
    job.complete(2, "checksum")
    assert job.status == RetrievalReadiness.INDEXED

