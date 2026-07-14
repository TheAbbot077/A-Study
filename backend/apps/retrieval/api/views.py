from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.retrieval.api.serializers import RetrievalIndexJobSummarySerializer, RetrievalReadinessSerializer
from apps.retrieval.models import RetrievalChunkCollection, RetrievalIndexJob
from apps.users.domain.models import InstitutionMembership


class InstitutionScopedReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def institution_ids(self):
        return InstitutionMembership.objects.filter(user=self.request.user, is_active=True).values_list("institution_id", flat=True)


class RetrievalReadinessViewSet(InstitutionScopedReadOnlyViewSet):
    serializer_class = RetrievalReadinessSerializer
    def get_queryset(self):
        return RetrievalChunkCollection.objects.filter(resource__subject__institution_id__in=self.institution_ids()).prefetch_related("index_jobs").order_by("-created_at")


class RetrievalIndexJobViewSet(InstitutionScopedReadOnlyViewSet):
    serializer_class = RetrievalIndexJobSummarySerializer
    def get_queryset(self):
        return RetrievalIndexJob.objects.filter(population_job__proposal__resource__subject__institution_id__in=self.institution_ids()).order_by("-created_at")

