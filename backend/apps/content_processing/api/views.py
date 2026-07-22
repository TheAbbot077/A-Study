from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.content_processing.api.serializers import (
    ContentProcessingJobSerializer,
    ProcessingAttemptSerializer,
    ProcessingDiagnosticSerializer,
    TeachingReadinessEvaluationSerializer,
)
from apps.content_processing.application import (
    CancelContentProcessingJobService,
    RetryContentProcessingJobService,
)
from apps.content_processing.domain.exceptions import ProcessingLifecycleError
from apps.content_processing.models import ContentProcessingJob, TeachingReadinessEvaluation
from apps.users.domain.models import InstitutionMembership


class ContentProcessingJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ContentProcessingJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ContentProcessingJob.objects.select_related("resource", "stored_file", "legacy_import_job").order_by("-created_at")
        institution_ids = list(
            InstitutionMembership.objects.filter(user=self.request.user, is_active=True).values_list("institution_id", flat=True)
        )
        if not institution_ids:
            return queryset.none()
        queryset = queryset.filter(resource__subject__institution_id__in=institution_ids)
        resource_id = self.request.query_params.get("resource")
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        return queryset

    @action(detail=True, methods=["get"], url_path="attempts")
    def attempts(self, request, pk=None):
        attempts = self.get_object().attempts.order_by("-attempt_number")
        return Response(ProcessingAttemptSerializer(attempts, many=True).data)

    @action(detail=True, methods=["get"], url_path="diagnostics")
    def diagnostics(self, request, pk=None):
        diagnostics = self.get_object().diagnostics.order_by("created_at")
        return Response(ProcessingDiagnosticSerializer(diagnostics, many=True).data)

    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, pk=None):
        try:
            job = RetryContentProcessingJobService().retry(self.get_object(), actor=request.user)
        except ProcessingLifecycleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ContentProcessingJobSerializer(job).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        try:
            job = CancelContentProcessingJobService().cancel(self.get_object(), actor=request.user)
        except ProcessingLifecycleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ContentProcessingJobSerializer(job).data, status=status.HTTP_200_OK)


class TeachingReadinessEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeachingReadinessEvaluationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        institution_ids = InstitutionMembership.objects.filter(
            user=self.request.user, is_active=True
        ).values_list("institution_id", flat=True)
        return TeachingReadinessEvaluation.objects.filter(
            resource__subject__institution_id__in=institution_ids
        ).order_by("-evaluated_at")
