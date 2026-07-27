import pytest
from rest_framework.test import APIClient

from apps.learning_identity.application.services import CreateLearningProfileService
from apps.users.models import Institution, InstitutionMembership


@pytest.mark.django_db
def test_learning_identity_profile_api_requires_authentication():
    response = APIClient().get("/api/learning-identity/profiles/")

    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_learning_identity_profile_list_and_detail_are_learner_scoped(django_user_model):
    learner = django_user_model.objects.create_user(email="memory-api@example.com", password="secret")
    other = django_user_model.objects.create_user(email="other-memory-api@example.com", password="secret")
    tenant = Institution.objects.create(name="Memory API", slug="memory-api")
    InstitutionMembership.objects.create(user=learner, institution=tenant, is_active=True)
    InstitutionMembership.objects.create(user=other, institution=tenant, is_active=True)
    profile = CreateLearningProfileService().execute(tenant=tenant, learner=learner, actor=learner)

    client = APIClient()
    client.force_authenticate(learner)
    listed = client.get("/api/learning-identity/profiles/")
    detail = client.get(f"/api/learning-identity/profiles/{profile.id}/")

    assert listed.status_code == 200
    assert listed.data[0]["profile_id"] == str(profile.id)
    assert detail.status_code == 200
    assert detail.data["profile_id"] == str(profile.id)

    client.force_authenticate(other)
    denied = client.get(f"/api/learning-identity/profiles/{profile.id}/")
    assert denied.status_code in {403, 404}


@pytest.mark.django_db
def test_learning_identity_preference_update_uses_expected_profile_version(django_user_model):
    learner = django_user_model.objects.create_user(email="preference-api@example.com", password="secret")
    tenant = Institution.objects.create(name="Preference API", slug="preference-api")
    InstitutionMembership.objects.create(user=learner, institution=tenant, is_active=True)
    profile = CreateLearningProfileService().execute(tenant=tenant, learner=learner, actor=learner)
    client = APIClient()
    client.force_authenticate(learner)

    response = client.post(
        f"/api/learning-identity/profiles/{profile.id}/preferences/",
        {
            "expected_profile_version": profile.version,
            "preference_key": "EXPLANATION_MODE",
            "value": "step_by_step",
            "idempotency_key": "api-pref",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["preference_key"] == "EXPLANATION_MODE"
