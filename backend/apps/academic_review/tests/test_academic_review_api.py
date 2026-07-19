import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_students_cannot_list_academic_reviews(django_user_model):
    student = django_user_model.objects.create_user(email="student-review@example.com", password="secret")
    client = APIClient(); client.force_authenticate(student)
    response = client.get("/api/academic-review/sessions/")
    assert response.status_code == 200
    assert response.data["count"] == 0


def test_anonymous_users_cannot_access_academic_review():
    response = APIClient().get("/api/academic-review/sessions/")
    assert response.status_code in {401, 403}
