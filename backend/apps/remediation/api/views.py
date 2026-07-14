from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.exceptions import DomainValidationError, LifecycleTransitionError
from apps.remediation.api.serializers import CreateRemediationPlanSerializer, PlanActionSerializer, RemediationPlanSerializer
from apps.remediation.application import RemediationExecutionService, RemediationHistoryService, RemediationPlanningService
from apps.remediation.domain.models import RemediationPlan, RemediationPlanStatus


class RemediationPlanViewSet(viewsets.ModelViewSet):
    serializer_class = RemediationPlanSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = (
            RemediationPlan.objects.filter(learner=self.request.user)
            .select_related("learner", "content_concept", "trigger_evidence")
            .order_by("-created_at")
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = CreateRemediationPlanSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        evidence = serializer.validated_data.get("evidence")
        if evidence:
            plan = RemediationPlanningService().plan_from_evidence(evidence)
            if plan is None:
                return Response({"detail": "Evidence does not require remediation."}, status=status.HTTP_400_BAD_REQUEST)
            return Response(RemediationPlanSerializer(plan).data, status=status.HTTP_201_CREATED)

        plan = RemediationPlan.objects.create(
            learner=request.user,
            content_concept=serializer.validated_data["content_concept"],
            rationale=serializer.validated_data.get("rationale", ""),
            metadata=serializer.validated_data.get("metadata", {}),
            status=RemediationPlanStatus.PENDING,
        )
        return Response(RemediationPlanSerializer(plan).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        plans = RemediationHistoryService().list_learner_plans(request.user)
        return Response(RemediationPlanSerializer(plans, many=True).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        try:
            plan = RemediationExecutionService().start_remediation(self.get_object())
        except (DomainValidationError, LifecycleTransitionError, DjangoValidationError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response(RemediationPlanSerializer(plan).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        try:
            plan = RemediationExecutionService().complete_remediation(self.get_object())
        except (DomainValidationError, LifecycleTransitionError, DjangoValidationError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response(RemediationPlanSerializer(plan).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = PlanActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            plan = RemediationExecutionService().cancel_remediation(self.get_object())
        except (DomainValidationError, LifecycleTransitionError, DjangoValidationError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response(RemediationPlanSerializer(plan).data)
