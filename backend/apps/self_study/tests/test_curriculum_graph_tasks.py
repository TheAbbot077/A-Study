from unittest.mock import Mock, patch

from apps.self_study.infrastructure.celery.tasks import build_curriculum_graph_task, validate_curriculum_graph_task


def test_graph_tasks_have_identifier_only_contracts():
    assert build_curriculum_graph_task.name == "self_study.build_curriculum_graph"
    assert validate_curriculum_graph_task.name == "self_study.validate_curriculum_graph"
    with patch("apps.self_study.infrastructure.celery.tasks.BuildCurriculumGraphService") as service_type:
        service_type.return_value = Mock()
        build_curriculum_graph_task.run("graph-version-id")
        service_type.return_value.execute.assert_called_once_with("graph-version-id")
    with patch("apps.self_study.infrastructure.celery.tasks.ValidateCurriculumGraphService") as service_type:
        service_type.return_value = Mock()
        validate_curriculum_graph_task.run("graph-version-id")
        service_type.return_value.execute.assert_called_once_with("graph-version-id")
