from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.exceptions import DomainValidationError, LifecycleTransitionError
from apps.assessment_review.api.serializers import (
    AssessmentReviewSerializer,
    CalibrationActionSerializer,
    DifficultyCalibrationSerializer,
    FindingActionSerializer,
    QuestionReviewSerializer,
    ReviewDecisionActionSerializer,
    ReviewerAssignmentSerializer,
)
from apps.assessment_review.application import (
    AssessmentAnalyticsService,
    AssessmentReviewService,
    DifficultyCalibrationService,
    QuestionReviewService,
    ReviewerAssignmentService,
)
from apps.assessment_review.domain.models import AssessmentReview, DifficultyCalibration, QuestionReview, ReviewerAssignment
from apps.assessments.domain.models import Assessment, ItemBankEntry


class AssessmentReviewViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentReviewSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = AssessmentReview.objects.select_related("assessment", "reviewer", "opened_by").order_by("-created_at")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        review = AssessmentReviewService().open_review(
            assessment=serializer.validated_data["assessment"],
            opened_by=self.request.user,
            reviewer=serializer.validated_data.get("reviewer"),
            metadata=serializer.validated_data.get("metadata", {}),
        )
        serializer.instance = review

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        reviews = AssessmentReviewService().list_pending_reviews()
        return Response(AssessmentReviewSerializer(reviews, many=True).data)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        try:
            review = AssessmentReviewService().start_review(self.get_object(), reviewer=request.user)
        except (DomainValidationError, LifecycleTransitionError, DjangoValidationError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response(AssessmentReviewSerializer(review).data)

    @action(detail=True, methods=["post"], url_path="findings")
    def findings(self, request, pk=None):
        serializer = FindingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        finding = AssessmentReviewService().record_finding(
            self.get_object(),
            finding_type=serializer.validated_data["finding_type"],
            severity=serializer.validated_data.get("severity", "medium"),
            description=serializer.validated_data["description"],
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response({"id": str(finding.id)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="decisions")
    def decisions(self, request, pk=None):
        serializer = ReviewDecisionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decision = AssessmentReviewService().record_decision(
                self.get_object(),
                decision=serializer.validated_data["decision"],
                decided_by=request.user,
                rationale=serializer.validated_data.get("rationale", ""),
                metadata=serializer.validated_data.get("metadata", {}),
            )
        except (DomainValidationError, LifecycleTransitionError, DjangoValidationError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response({"id": str(decision.id)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="analytics")
    def analytics(self, request, pk=None):
        return Response(AssessmentAnalyticsService().assessment_metrics(self.get_object().assessment))


class QuestionReviewViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionReviewSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = QuestionReview.objects.select_related("item_bank_entry", "reviewer", "opened_by").order_by("-created_at")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        review = QuestionReviewService().open_review(
            item_bank_entry=serializer.validated_data["item_bank_entry"],
            opened_by=self.request.user,
            reviewer=serializer.validated_data.get("reviewer"),
            metadata=serializer.validated_data.get("metadata", {}),
        )
        serializer.instance = review

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        reviews = QuestionReviewService().list_pending_reviews()
        return Response(QuestionReviewSerializer(reviews, many=True).data)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        try:
            review = QuestionReviewService().start_review(self.get_object(), reviewer=request.user)
        except (DomainValidationError, LifecycleTransitionError, DjangoValidationError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response(QuestionReviewSerializer(review).data)

    @action(detail=True, methods=["post"], url_path="findings")
    def findings(self, request, pk=None):
        serializer = FindingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        finding = QuestionReviewService().record_finding(
            self.get_object(),
            finding_type=serializer.validated_data["finding_type"],
            severity=serializer.validated_data.get("severity", "medium"),
            description=serializer.validated_data["description"],
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response({"id": str(finding.id)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="decisions")
    def decisions(self, request, pk=None):
        serializer = ReviewDecisionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decision = QuestionReviewService().record_decision(
                self.get_object(),
                decision=serializer.validated_data["decision"],
                decided_by=request.user,
                rationale=serializer.validated_data.get("rationale", ""),
                metadata=serializer.validated_data.get("metadata", {}),
            )
        except (DomainValidationError, LifecycleTransitionError, DjangoValidationError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response({"id": str(decision.id)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="analytics")
    def analytics(self, request, pk=None):
        return Response(AssessmentAnalyticsService().question_metrics(self.get_object().item_bank_entry))


class ReviewerAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewerAssignmentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return ReviewerAssignment.objects.select_related("reviewer", "assessment_review", "question_review").order_by("-assigned_at")

    def perform_create(self, serializer):
        service = ReviewerAssignmentService()
        if serializer.validated_data.get("assessment_review"):
            assignment = service.assign_assessment_review(
                serializer.validated_data["assessment_review"],
                serializer.validated_data["reviewer"],
                metadata=serializer.validated_data.get("metadata", {}),
            )
        else:
            assignment = service.assign_question_review(
                serializer.validated_data["question_review"],
                serializer.validated_data["reviewer"],
                metadata=serializer.validated_data.get("metadata", {}),
            )
        serializer.instance = assignment

    @action(detail=False, methods=["get"], url_path="workload")
    def workload(self, request):
        return Response(ReviewerAssignmentService().reviewer_workload(request.user))


class DifficultyCalibrationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DifficultyCalibrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DifficultyCalibration.objects.select_related("assessment", "item_bank_entry").order_by("-created_at")

    @action(detail=False, methods=["post"], url_path="calibrate")
    def calibrate(self, request):
        serializer = CalibrationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = get_object_or_404(ItemBankEntry, id=serializer.validated_data["item_bank_entry"])
        assessment = None
        if serializer.validated_data.get("assessment"):
            assessment = get_object_or_404(Assessment, id=serializer.validated_data["assessment"])
        try:
            calibration = DifficultyCalibrationService().calibrate_item(
                item,
                observed_success_rate=serializer.validated_data.get("observed_success_rate"),
                sample_size=serializer.validated_data["sample_size"],
                assessment=assessment,
                metadata=serializer.validated_data.get("metadata", {}),
            )
        except (DomainValidationError, LifecycleTransitionError, DjangoValidationError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response(DifficultyCalibrationSerializer(calibration).data, status=status.HTTP_201_CREATED)


class AssessmentReviewAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(AssessmentAnalyticsService().platform_metrics())
