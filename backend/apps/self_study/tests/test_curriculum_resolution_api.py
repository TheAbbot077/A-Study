import pytest
from rest_framework.test import APIClient

from apps.self_study.api.curriculum_serializers import StartResolutionSerializer
from apps.users.models import Institution, InstitutionMembership, InstitutionRole


def test_resolution_request_rejects_client_controlled_scores_and_failures():
    serializer = StartResolutionSerializer(
        data={
            "idempotency_key": "key",
            "candidate_scores": {"version": 100},
            "failure_reason": "NO_CURRICULA_REGISTERED",
        }
    )
    assert serializer.is_valid() is False
    assert "code" in serializer.errors


def test_registry_and_resolution_routes_require_authentication():
    client = APIClient()
    assert client.get("/api/curricula/").status_code in {401, 403}
    assert client.post("/api/curriculum-registry/authorities/", {}).status_code in {401, 403}


@pytest.mark.django_db
def test_learner_cannot_create_or_verify_registry_authority(django_user_model):
    learner = django_user_model.objects.create_user(email="registry-learner@example.com", password="secret")
    client = APIClient()
    client.force_authenticate(learner)
    response = client.post(
        "/api/curriculum-registry/authorities/",
        {
            "canonical_key": "learner-claimed",
            "name": "Learner Claimed Authority",
            "authority_type": "LEARNER_SUPPLIED",
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_tenant_administrator_can_register_tenant_scoped_authority(django_user_model):
    administrator = django_user_model.objects.create_user(email="registry-owner@example.com", password="secret")
    tenant = Institution.objects.create(name="Registry school", slug="registry-school")
    InstitutionMembership.objects.create(
        user=administrator,
        institution=tenant,
        role=InstitutionRole.ADMINISTRATOR,
    )
    client = APIClient()
    client.force_authenticate(administrator)
    response = client.post(
        "/api/curriculum-registry/authorities/",
        {
            "canonical_key": "registry-school",
            "name": "Registry School",
            "authority_type": "ACCREDITED_INSTITUTION",
            "tenant_id": str(tenant.id),
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["verification_status"] == "UNVERIFIED"
