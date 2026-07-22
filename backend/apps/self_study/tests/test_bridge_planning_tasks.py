from apps.self_study.infrastructure.celery.tasks import create_bridge_plan_task, finalize_bridge_plan_task


def test_bridge_tasks_have_stable_names_and_identifier_only_signatures():
    assert create_bridge_plan_task.name == "self_study.create_bridge_plan"
    assert finalize_bridge_plan_task.name == "self_study.finalize_bridge_plan"
    assert list(create_bridge_plan_task.run.__annotations__) == ["run_id", "return"]
    assert list(finalize_bridge_plan_task.run.__annotations__) == ["run_id", "return"]
