from unittest.mock import Mock,patch
from apps.self_study.infrastructure.celery.tasks import build_content_evidence_task,generate_evidence_candidates_task,evaluate_curriculum_coverage_task
def test_mapping_tasks_are_stable_and_identifier_only():
 assert build_content_evidence_task.name=="self_study.build_content_evidence"
 assert generate_evidence_candidates_task.name=="self_study.generate_evidence_mapping_candidates"
 assert evaluate_curriculum_coverage_task.name=="self_study.evaluate_curriculum_coverage"
 with patch("apps.self_study.infrastructure.celery.tasks.BuildContentEvidenceService") as service:
  service.return_value=Mock();build_content_evidence_task.run("run-id");service.return_value.execute.assert_called_once_with("run-id")
