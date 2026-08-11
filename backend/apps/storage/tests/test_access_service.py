import pytest

from apps.storage.domain.models import StoredFile, StoredFileSecurityScope
from apps.storage.services.access_service import ResolveStoredFileAccessService, StoredFileAccessOperation
from apps.users.domain.models import Institution, InstitutionMembership, InstitutionRole, User


@pytest.mark.django_db
def test_private_file_is_visible_to_owner_only():
    owner = User.objects.create_user(email="owner@example.com", password="password")
    other = User.objects.create_user(email="other@example.com", password="password")
    stored_file = StoredFile.objects.create(
        original_filename="note.txt",
        stored_filename="stored-note.txt",
        content_type="text/plain",
        size_bytes=5,
        checksum="abc123",
        provider="local",
        owner=owner,
        security_scope=StoredFileSecurityScope.PRIVATE_LEARNER,
    )

    service = ResolveStoredFileAccessService()

    assert service.resolve(owner, stored_file, operation=StoredFileAccessOperation.VIEW).allowed is True
    assert service.resolve(other, stored_file, operation=StoredFileAccessOperation.VIEW).allowed is False


@pytest.mark.django_db
def test_institution_shared_file_requires_matching_membership():
    institution = Institution.objects.create(name="Example School", slug="example-school")
    member = User.objects.create_user(email="member@example.com", password="password")
    outsider = User.objects.create_user(email="outsider@example.com", password="password")
    InstitutionMembership.objects.create(user=member, institution=institution, role=InstitutionRole.STUDENT, is_active=True)
    stored_file = StoredFile.objects.create(
        original_filename="shared.pdf",
        stored_filename="stored-shared.pdf",
        content_type="application/pdf",
        size_bytes=10,
        checksum="abc123",
        provider="local",
        tenant=institution,
        security_scope=StoredFileSecurityScope.INSTITUTION_SHARED,
    )

    service = ResolveStoredFileAccessService()

    assert service.resolve(member, stored_file, operation=StoredFileAccessOperation.VIEW).allowed is True
    assert service.resolve(outsider, stored_file, operation=StoredFileAccessOperation.VIEW).allowed is False


@pytest.mark.django_db
def test_accessible_queryset_filters_out_foreign_files():
    owner = User.objects.create_user(email="owner@example.com", password="password")
    other = User.objects.create_user(email="other@example.com", password="password")
    institution = Institution.objects.create(name="Example School", slug="example-school")
    InstitutionMembership.objects.create(user=owner, institution=institution, role=InstitutionRole.STUDENT, is_active=True)

    own_file = StoredFile.objects.create(
        original_filename="own.txt",
        stored_filename="own-stored.txt",
        content_type="text/plain",
        size_bytes=4,
        checksum="abc",
        provider="local",
        owner=owner,
        security_scope=StoredFileSecurityScope.PRIVATE_LEARNER,
    )
    StoredFile.objects.create(
        original_filename="foreign.txt",
        stored_filename="foreign-stored.txt",
        content_type="text/plain",
        size_bytes=4,
        checksum="def",
        provider="local",
        owner=other,
        security_scope=StoredFileSecurityScope.PRIVATE_LEARNER,
    )

    service = ResolveStoredFileAccessService()
    queryset = service.accessible_queryset(owner, operation=StoredFileAccessOperation.VIEW)

    assert list(queryset.values_list("id", flat=True)) == [own_file.id]
