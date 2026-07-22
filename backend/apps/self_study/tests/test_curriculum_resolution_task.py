from unittest.mock import Mock, patch

from apps.self_study.infrastructure.celery.tasks import resolve_curriculum_task


def test_curriculum_task_name_and_identifier_only_contract():
    assert resolve_curriculum_task.name == "self_study.resolve_curriculum"
    with patch(
        "apps.self_study.infrastructure.celery.tasks.ResolveCurriculumAttemptService"
    ) as service_type:
        service = Mock()
        service_type.return_value = service
        resolve_curriculum_task.run("attempt-id")
    service.execute.assert_called_once_with("attempt-id")
