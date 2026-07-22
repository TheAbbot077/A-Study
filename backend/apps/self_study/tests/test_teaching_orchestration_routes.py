from django.urls import reverse


def test_teaching_session_routes_are_registered():
    assert reverse("teaching-session-list").endswith("/teaching-sessions/")
    assert reverse("teaching-session-detail", kwargs={"pk": "11111111-1111-4111-8111-111111111111"}).endswith("/teaching-sessions/11111111-1111-4111-8111-111111111111/")


def test_teaching_session_command_routes_are_explicit():
    session_id = "11111111-1111-4111-8111-111111111111"
    assert reverse("teaching-session-next-turn", kwargs={"pk": session_id}).endswith(f"/teaching-sessions/{session_id}/next-turn/")
    assert reverse("teaching-session-learner-turn", kwargs={"pk": session_id}).endswith(f"/teaching-sessions/{session_id}/learner-turn/")
    assert reverse("teaching-session-request-evaluation", kwargs={"pk": session_id}).endswith(f"/teaching-sessions/{session_id}/request-evaluation/")
    assert reverse("teaching-session-handoff", kwargs={"pk": session_id}).endswith(f"/teaching-sessions/{session_id}/handoff/")
