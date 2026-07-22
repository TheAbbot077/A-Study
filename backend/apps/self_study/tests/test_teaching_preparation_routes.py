from django.urls import reverse


def test_teaching_preparation_routes_are_registered():
    assert reverse("teaching-preparation-run-list").endswith("/teaching-preparation-runs/")
    assert reverse("teaching-preparation-detail", kwargs={"pk": "11111111-1111-4111-8111-111111111111"}).endswith("/teaching-preparations/11111111-1111-4111-8111-111111111111/")


def test_teaching_preparation_handoff_route_is_explicit():
    target = reverse("teaching-preparation-current-handoff", kwargs={"intent_id": "11111111-1111-4111-8111-111111111111"})
    assert target.endswith("/teaching-preparations/current-handoff/11111111-1111-4111-8111-111111111111/")
