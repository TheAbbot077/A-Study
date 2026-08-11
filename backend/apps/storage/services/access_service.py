from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q, QuerySet

from apps.storage.domain.models import StoredFile, StoredFileSecurityScope
from apps.users.domain.models import InstitutionMembership, InstitutionRole, User


class StoredFileAccessOperation:
    VIEW = "view"
    DOWNLOAD = "download"
    DELETE = "delete"
    REFERENCE = "reference"
    ATTACH = "attach"
    ADMINISTER = "administer"


STAFF_ROLES = {
    InstitutionRole.TEACHER,
    InstitutionRole.ADMINISTRATOR,
    InstitutionRole.INSTITUTION_OWNER,
    InstitutionRole.SYSTEM_ADMINISTRATOR,
}


@dataclass(frozen=True)
class StoredFileAccessDecision:
    allowed: bool
    reason_code: str
    operation: str


class ResolveStoredFileAccessService:
    def accessible_queryset(self, actor: User | None, *, operation: str = StoredFileAccessOperation.VIEW) -> QuerySet[StoredFile]:
        if actor is None or not getattr(actor, "is_authenticated", False):
            return StoredFile.objects.none()
        if getattr(actor, "is_superuser", False):
            return StoredFile.objects.all().order_by("-created_at")

        membership_ids = list(
            InstitutionMembership.objects.filter(user=actor, is_active=True).values_list("institution_id", flat=True)
        )
        if operation == StoredFileAccessOperation.VIEW:
            return StoredFile.objects.filter(
                Q(owner_id=actor.id)
                | Q(security_scope=StoredFileSecurityScope.INSTITUTION_SHARED, tenant_id__in=membership_ids)
            ).distinct().order_by("-created_at")

        if operation in {StoredFileAccessOperation.DOWNLOAD, StoredFileAccessOperation.REFERENCE, StoredFileAccessOperation.ATTACH}:
            return StoredFile.objects.filter(
                Q(owner_id=actor.id)
                | Q(security_scope=StoredFileSecurityScope.INSTITUTION_SHARED, tenant_id__in=membership_ids)
            ).distinct().order_by("-created_at")

        if operation in {StoredFileAccessOperation.DELETE, StoredFileAccessOperation.ADMINISTER}:
            staff_institutions = list(
                InstitutionMembership.objects.filter(
                    user=actor,
                    is_active=True,
                    role__in=STAFF_ROLES,
                ).values_list("institution_id", flat=True)
            )
            return StoredFile.objects.filter(
                Q(owner_id=actor.id)
                | Q(security_scope=StoredFileSecurityScope.INSTITUTION_SHARED, tenant_id__in=staff_institutions)
            ).distinct().order_by("-created_at")

        return StoredFile.objects.none()

    def resolve(self, actor: User | None, stored_file: StoredFile, *, operation: str) -> StoredFileAccessDecision:
        if actor is None or not getattr(actor, "is_authenticated", False):
            return StoredFileAccessDecision(False, "STORED_FILE_ACCESS_DENIED", operation)

        if getattr(actor, "is_superuser", False):
            return StoredFileAccessDecision(True, "", operation)

        if stored_file.security_scope == StoredFileSecurityScope.LEGACY_RESTRICTED:
            return StoredFileAccessDecision(False, "STORED_FILE_LEGACY_RESTRICTED", operation)

        if stored_file.security_scope == StoredFileSecurityScope.SYSTEM_MANAGED:
            return StoredFileAccessDecision(False, "STORED_FILE_ACCESS_DENIED", operation)

        if operation in {StoredFileAccessOperation.VIEW, StoredFileAccessOperation.DOWNLOAD, StoredFileAccessOperation.REFERENCE, StoredFileAccessOperation.ATTACH}:
            if stored_file.owner_id == actor.id:
                return StoredFileAccessDecision(True, "", operation)

            if (
                stored_file.security_scope == StoredFileSecurityScope.INSTITUTION_SHARED
                and stored_file.tenant_id is not None
                and InstitutionMembership.objects.filter(
                    user=actor,
                    institution_id=stored_file.tenant_id,
                    is_active=True,
                ).exists()
            ):
                return StoredFileAccessDecision(True, "", operation)

            return StoredFileAccessDecision(False, "STORED_FILE_ACCESS_DENIED", operation)

        if operation in {StoredFileAccessOperation.DELETE, StoredFileAccessOperation.ADMINISTER}:
            if stored_file.owner_id == actor.id:
                return StoredFileAccessDecision(True, "", operation)

            if (
                stored_file.security_scope == StoredFileSecurityScope.INSTITUTION_SHARED
                and stored_file.tenant_id is not None
                and InstitutionMembership.objects.filter(
                    user=actor,
                    institution_id=stored_file.tenant_id,
                    is_active=True,
                    role__in=STAFF_ROLES,
                ).exists()
            ):
                return StoredFileAccessDecision(True, "", operation)

            return StoredFileAccessDecision(False, "STORED_FILE_ACCESS_DENIED", operation)

        return StoredFileAccessDecision(False, "STORED_FILE_OPERATION_NOT_PERMITTED", operation)
