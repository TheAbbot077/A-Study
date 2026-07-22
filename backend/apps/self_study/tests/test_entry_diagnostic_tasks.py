from unittest.mock import Mock,patch
from apps.self_study.infrastructure.celery.tasks import finalize_diagnostic_placement_task

def test_finalization_task_accepts_identifier_only_and_is_named():
    assert finalize_diagnostic_placement_task.name=="self_study.finalize_diagnostic_placement"
    with patch("apps.self_study.infrastructure.celery.tasks.FinalizeDiagnosticPlacementService") as service:
        service.return_value=Mock();finalize_diagnostic_placement_task.run("diagnostic-id");service.return_value.execute.assert_called_once_with("diagnostic-id")
