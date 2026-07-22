import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.self_study.curriculum_models import (
    CurriculumAuthority,
    CurriculumReference,
    CurriculumVersion,
)


@pytest.mark.django_db
def test_authority_verification_and_suspension_are_explicit(django_user_model):
    administrator = django_user_model.objects.create_user(email="registry-admin@example.com", password="secret")
    authority = CurriculumAuthority.objects.create(
        canonical_key="national-body",
        name="National Body",
        authority_type="NATIONAL_CURRICULUM_BODY",
    )
    assert authority.verification_status == "UNVERIFIED"
    authority.verify(administrator)
    authority.save()
    assert authority.verification_status == "VERIFIED"
    assert authority.verified_at is not None
    authority.suspend()
    authority.save()
    assert authority.verification_status == "SUSPENDED"
    assert authority.status == "SUSPENDED"


@pytest.mark.django_db
def test_version_activation_requires_verified_authority_and_complete_provenance(django_user_model):
    administrator = django_user_model.objects.create_user(email="version-admin@example.com", password="secret")
    authority = CurriculumAuthority.objects.create(
        canonical_key="qualification-body",
        name="Qualification Body",
        authority_type="QUALIFICATION_PROVIDER",
    )
    reference = CurriculumReference.objects.create(
        canonical_key="advanced-mathematics",
        title="Advanced Mathematics",
        subject_area="mathematics",
        authority=authority,
        source_classification="INSTITUTION_OR_QUALIFICATION",
        language="en",
    )
    version = CurriculumVersion.objects.create(
        curriculum_reference=reference,
        version_label="2026",
        canonical_source_uri="https://example.edu/mathematics",
        content_hash="sha256:one",
        licence_identifier="CC-BY",
        provenance_status="INCOMPLETE",
        language="en",
        created_by=administrator,
    )
    with pytest.raises(ValidationError) as incomplete:
        version.activate()
    assert incomplete.value.code == "CURRICULUM_PROVENANCE_INCOMPLETE"
    authority.verification_status = "VERIFIED"
    authority.verified_at = timezone.now()
    authority.verified_by = administrator
    authority.save()
    version.provenance_status = "COMPLETE"
    version.activate()
    version.save()
    assert version.status == "ACTIVE"


@pytest.mark.django_db
def test_active_resolution_fields_are_immutable(django_user_model):
    administrator = django_user_model.objects.create_user(email="immutable-admin@example.com", password="secret")
    authority = CurriculumAuthority.objects.create(
        canonical_key="verified-body",
        name="Verified Body",
        authority_type="GOVERNMENT",
        verification_status="VERIFIED",
        verified_at=timezone.now(),
        verified_by=administrator,
    )
    reference = CurriculumReference.objects.create(
        canonical_key="official-mathematics",
        title="Official Mathematics",
        subject_area="mathematics",
        authority=authority,
        source_classification="NATIONAL_OR_REGIONAL",
        language="en",
    )
    version = CurriculumVersion.objects.create(
        curriculum_reference=reference,
        version_label="2026",
        status="ACTIVE",
        canonical_source_uri="https://example.gov/math",
        content_hash="sha256:original",
        licence_identifier="PUBLIC",
        provenance_status="COMPLETE",
        language="en",
        created_by=administrator,
    )
    version.content_hash = "sha256:changed"
    with pytest.raises(ValidationError):
        version.save()
