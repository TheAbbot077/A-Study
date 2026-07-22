from django.urls import reverse


def test_bridge_planning_routes_are_registered():
    assert reverse("bridge-planning-run-list").endswith("/bridge-planning-runs/")
    assert reverse("bridge-plan-detail", kwargs={"pk": "11111111-1111-4111-8111-111111111111"}).endswith("/bridge-plans/11111111-1111-4111-8111-111111111111/")


def test_bridge_handoff_route_is_explicit():
    target = reverse("bridge-plan-current-handoff", kwargs={"intent_id": "11111111-1111-4111-8111-111111111111"})
    assert target.endswith("/bridge-plans/current-handoff/11111111-1111-4111-8111-111111111111/")
