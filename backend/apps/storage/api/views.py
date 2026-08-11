from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.storage.api.serializers import StoredFileSerializer, StoredFileUploadSerializer
from apps.storage.domain.models import StoredFile, StoredFileSecurityScope
from apps.storage.infrastructure.providers import LocalStorageProvider
from apps.storage.services import ResolveStoredFileAccessService, StorageService, StoredFileAccessOperation
from apps.users.domain.models import InstitutionMembership


class StoredFileViewSet(viewsets.GenericViewSet):
    queryset = StoredFile.objects.none()
    serializer_class = StoredFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "storage-upload"
    http_method_names = ["get", "post", "delete", "head", "options"]

    access_service = ResolveStoredFileAccessService()

    def get_queryset(self):
        return self.access_service.accessible_queryset(self.request.user, operation=StoredFileAccessOperation.VIEW)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        stored_file = get_object_or_404(self.get_queryset(), id=kwargs["pk"])
        return Response(StoredFileSerializer(stored_file).data)

    def create(self, request, *args, **kwargs):
        serializer = StoredFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data["file"]
        tenant = self._default_tenant(request.user)
        stored_file = StorageService(provider=LocalStorageProvider()).store_file(
            uploaded_file.file,
            original_filename=uploaded_file.name,
            content_type=uploaded_file.content_type,
            owner=request.user,
            tenant=tenant,
            security_scope=StoredFileSecurityScope.PRIVATE_LEARNER,
        )
        return Response(StoredFileSerializer(stored_file).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        stored_file = get_object_or_404(self.get_queryset(), id=kwargs["pk"])
        decision = self.access_service.resolve(request.user, stored_file, operation=StoredFileAccessOperation.ADMINISTER)
        if not decision.allowed:
            raise PermissionDenied(detail={"code": decision.reason_code})

        StorageService(provider=LocalStorageProvider()).delete_file(stored_file)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _default_tenant(self, actor):
        memberships = list(
            InstitutionMembership.objects.select_related("institution").filter(user=actor, is_active=True)[:2]
        )
        if len(memberships) != 1:
            return None
        return memberships[0].institution
