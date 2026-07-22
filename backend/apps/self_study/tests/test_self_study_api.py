import pytest
from rest_framework.test import APIClient

from apps.academic.models import Subject
from apps.self_study.models import LearningPolicyRuleSet
from apps.users.models import Institution


def create_scope(django_user_model, suffix="one"):
    user = django_user_model.objects.create_user(email=f"learner-{suffix}@example.com", password="secret")
    tenant = Institution.objects.create(name=f"Tenant {suffix}", slug=f"tenant-{suffix}")
    subject = Subject.objects.create(institution=tenant, code=f"MATH-{suffix}", name="Mathematics")
    return user, tenant, subject


def platform_policy():
    LearningPolicyRuleSet.objects.filter(
        authority=LearningPolicyRuleSet.Authority.PLATFORM,
        is_active=True,
    ).update(is_active=False)
    return LearningPolicyRuleSet.objects.create(
        authority=LearningPolicyRuleSet.Authority.PLATFORM,
        allowed_provider_ids=["open-provider"],
        allowed_source_categories=["OPEN_EDUCATIONAL_RESOURCE"],
        allowed_licence_categories=["CC-BY"],
        allowed_mime_types=["application/pdf"],
        allowed_languages=["en"],
        maximum_resource_count=10,
        maximum_single_file_bytes=10_000,
        maximum_total_bytes=50_000,
        maximum_cost="0.00",
        external_network_access_enabled=True,
    )


@pytest.mark.django_db
def test_authentication_is_required():
    response = APIClient().get("/api/self-study/intents/")
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_create_ready_activate_and_public_policy_do_not_leak_scores(django_user_model):
    learner, tenant, subject = create_scope(django_user_model)
    platform_policy()
    client = APIClient()
    client.force_authenticate(learner)
    created = client.post(
        "/api/self-study/intents/",
        {
            "tenant_id": str(tenant.id),
            "subject_id": str(subject.id),
            "mode": "SELF_STUDY",
            "goal_statement": "Prepare for first-year calculus.",
            "preferred_language": "en",
            "policy_acknowledged": True,
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    ready = client.post(
        f"/api/self-study/intents/{created.data['id']}/ready/",
        {"expected_version": created.data["version"]},
        format="json",
    )
    assert ready.status_code == 200
    active = client.post(
        f"/api/self-study/intents/{created.data['id']}/activate/",
        {"expected_version": ready.data["version"]},
        format="json",
    )
    assert active.status_code == 200
    response = client.get(f"/api/self-study/intents/{created.data['id']}/policy/")
    assert response.status_code == 200
    encoded = str(response.data)
    assert "raw_scores_visible" not in encoded
    assert "comparative_ranking_allowed" not in encoded
    assert response.data["diagnostic_disclosure"]["formal_grade_effect"] is False
    assert response.data["diagnostic_disclosure"]["transcript_effect"] is False


@pytest.mark.django_db
def test_incomplete_intent_returns_stable_ready_blocker(django_user_model):
    learner, tenant, subject = create_scope(django_user_model)
    client = APIClient()
    client.force_authenticate(learner)
    created = client.post(
        "/api/self-study/intents/",
        {
            "tenant_id": str(tenant.id),
            "subject_id": str(subject.id),
            "mode": "SELF_STUDY",
            "goal_statement": "",
            "preferred_language": "en",
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    assert created.data["id"]
    assert created.data["version"] == 1
    assert created.data["status"] == "DRAFT"
    response = client.post(
        f"/api/self-study/intents/{created.data['id']}/ready/",
        {"expected_version": created.data["version"]},
        format="json",
    )
    assert response.status_code == 422
    assert response.data["code"] == "LEARNING_GOAL_REQUIRED"


@pytest.mark.django_db
def test_cross_tenant_access_does_not_confirm_object_existence(django_user_model):
    owner, tenant, subject = create_scope(django_user_model, "owner")
    stranger, _, _ = create_scope(django_user_model, "stranger")
    intent = owner.self_study_intents.create(
        tenant=tenant,
        subject=subject,
        mode="SELF_STUDY",
        goal_statement="Learn safely",
        preferred_language="en",
        created_by=owner,
    )
    client = APIClient()
    client.force_authenticate(stranger)
    response = client.get(f"/api/self-study/intents/{intent.id}/")
    assert response.status_code == 404
    assert "access" not in str(response.data).lower()


@pytest.mark.django_db
def test_trailing_slash_is_canonical(django_user_model):
    learner, _, _ = create_scope(django_user_model, "slash")
    client = APIClient()
    client.force_authenticate(learner)
    assert client.get("/api/self-study/intents/").status_code == 200
