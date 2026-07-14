from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academic.domain.models import LearningResource
from apps.content_intelligence.api.serializers import (
    ContentImportJobSerializer,
    ContentValidationFindingSerializer,
    CreateImportJobSerializer,
    ParsedDocumentSerializer,
    RetryImportJobSerializer,
)
from apps.content_intelligence.application import ContentImportDeletionService, ImportService
from apps.content_intelligence.domain.exceptions import ContentImportDeletionConflictError, ContentImportDeletionError
from apps.content_processing.domain.exceptions import ProcessingLifecycleError
from apps.content_intelligence.models import ContentImportJob
from apps.core.events import EventPublisher
from apps.storage.infrastructure.providers import LocalStorageProvider
from apps.storage.services.storage_service import StorageService
from apps.users.domain.models import InstitutionMembership


class ContentImportJobViewSet(viewsets.ModelViewSet):
    serializer_class = ContentImportJobSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        queryset = ContentImportJob.objects.select_related("learning_resource", "stored_file", "requested_by").order_by("-created_at")
        institution_ids = list(
            InstitutionMembership.objects.filter(user=self.request.user, is_active=True).values_list("institution_id", flat=True)
        )
        if not institution_ids:
            return queryset.none()
        queryset = queryset.filter(learning_resource__subject__institution_id__in=institution_ids)
        learning_resource_id = self.request.query_params.get("learning_resource")
        if learning_resource_id:
            queryset = queryset.filter(learning_resource_id=learning_resource_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = CreateImportJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        learning_resource = get_object_or_404(LearningResource, id=serializer.validated_data["learning_resource"])
        job = ImportService().create_import_job(
            learning_resource=learning_resource,
            requested_by=request.user,
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response(ContentImportJobSerializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="outline")
    def outline(self, request, pk=None):
        parsed_document = getattr(self.get_object(), "parsed_document", None)
        if parsed_document is None:
            return Response({"detail": "No parsed document is available for this import job."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ParsedDocumentSerializer(parsed_document).data)

    @action(detail=True, methods=["get"], url_path="findings")
    def findings(self, request, pk=None):
        findings = self.get_object().validation_findings.all().order_by("-created_at")
        return Response(ContentValidationFindingSerializer(findings, many=True).data)

    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, pk=None):
        serializer = RetryImportJobSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            job = ImportService().retry_failed_import(self.get_object())
        except ProcessingLifecycleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ContentImportJobSerializer(job).data)

    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        storage_service = StorageService(provider=LocalStorageProvider(), event_publisher=EventPublisher())
        try:
            ContentImportDeletionService(storage_service=storage_service).delete_import(job)
        except ContentImportDeletionConflictError as exc:
            return Response(
                {"detail": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_409_CONFLICT,
            )
        except ContentImportDeletionError as exc:
            return Response(
                {"detail": str(exc), "code": exc.code, "details": exc.details},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
