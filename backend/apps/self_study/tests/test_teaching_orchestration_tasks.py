from apps.self_study.infrastructure.celery.tasks import (
    advance_teaching_session_task,
    generate_teaching_turn_task,
    prepare_teaching_turn_task,
    record_teaching_evidence_task,
)


def test_teaching_orchestration_tasks_have_stable_names_and_identifier_only_signatures():
    assert prepare_teaching_turn_task.name == "self_study.prepare_teaching_turn"
    assert generate_teaching_turn_task.name == "self_study.generate_teaching_turn"
    assert record_teaching_evidence_task.name == "self_study.record_teaching_evidence"
    assert advance_teaching_session_task.name == "self_study.advance_teaching_session"
    assert list(prepare_teaching_turn_task.run.__annotations__) == ["session_id", "return"]
    assert list(generate_teaching_turn_task.run.__annotations__) == ["session_id", "return"]
    assert list(record_teaching_evidence_task.run.__annotations__) == ["session_id", "return"]
    assert list(advance_teaching_session_task.run.__annotations__) == ["session_id", "return"]
