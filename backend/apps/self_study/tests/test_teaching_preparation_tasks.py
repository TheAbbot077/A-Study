from apps.self_study.infrastructure.celery.tasks import (
    assemble_teaching_preparation_task,
    evaluate_teaching_readiness_task,
    publish_teaching_retrieval_task,
)


def test_teaching_preparation_tasks_have_stable_names_and_identifier_only_signatures():
    assert assemble_teaching_preparation_task.name == "self_study.assemble_teaching_preparation"
    assert publish_teaching_retrieval_task.name == "self_study.publish_teaching_retrieval"
    assert evaluate_teaching_readiness_task.name == "self_study.evaluate_teaching_readiness"
    assert list(assemble_teaching_preparation_task.run.__annotations__) == ["run_id", "return"]
    assert list(publish_teaching_retrieval_task.run.__annotations__) == ["retrieval_manifest_id", "return"]
    assert list(evaluate_teaching_readiness_task.run.__annotations__) == ["manifest_id", "return"]
