from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.text import slugify

from apps.academic.api.serializers import (
    ContentConceptSerializer,
    ContentSectionSerializer,
    CurriculumSerializer,
    CurriculumUnitSerializer,
    IngestionFailureSerializer,
    LearningResourceSerializer,
    QualityMarkSerializer,
    ResourceIngestionJobSerializer,
    ReviewActionSerializer,
    SubjectSerializer,
)
from apps.academic.domain.models import (
    ContentConcept,
    ContentSection,
    Curriculum,
    CurriculumUnit,
    LearningResource,
    ResourceIngestionJob,
    Subject,
)
from apps.academic.services import (
    AcademicStructureService,
    ContentReviewService,
    CurriculumService,
    LearningResourceService,
    ManualAuthoringService,
    ResourceIngestionService,
)
from apps.users.domain.models import Institution, InstitutionMembership


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        institution_ids = list(
            InstitutionMembership.objects.filter(user=self.request.user, is_active=True).values_list("institution_id", flat=True)
        )
        queryset = Subject.objects.all().order_by("code")
        if not institution_ids:
            return queryset.none()
        return queryset.filter(institution_id__in=institution_ids)

    def _resolve_institution(self, serializer):
        institution = serializer.validated_data.get("institution")
        if institution is not None:
            return institution

        membership = InstitutionMembership.objects.select_related("institution").filter(user=self.request.user, is_active=True).order_by("created_at").first()
        if membership is not None:
            return membership.institution

        institution = Institution.objects.create(
            name=f"{self.request.user.email.split('@')[0]}'s Study Space",
            slug=f"{slugify(self.request.user.email.split('@')[0]) or 'learner'}-{str(self.request.user.id)[:8]}",
        )
        InstitutionMembership.objects.create(user=self.request.user, institution=institution, is_active=True)
        return institution

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        data["institution"] = self._resolve_institution(serializer)
        self.instance = AcademicStructureService().create_subject(**data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(self.instance).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        self.instance = AcademicStructureService().update_subject(serializer.instance, **serializer.validated_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(self.get_serializer(self.instance).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        subject = AcademicStructureService().archive_subject(self.get_object())
        return Response(self.get_serializer(subject).data)


class CurriculumViewSet(viewsets.ModelViewSet):
    queryset = Curriculum.objects.all().order_by("subject", "name", "version")
    serializer_class = CurriculumSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def perform_create(self, serializer):
        data = serializer.validated_data
        self.instance = CurriculumService().create_curriculum(**data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(self.instance).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        self.instance = CurriculumService().update_curriculum(serializer.instance, **serializer.validated_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(self.get_serializer(self.instance).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        curriculum = CurriculumService().archive_curriculum(self.get_object())
        return Response(self.get_serializer(curriculum).data)


class CurriculumUnitViewSet(viewsets.ModelViewSet):
    queryset = CurriculumUnit.objects.all().order_by("curriculum", "sequence_number")
    serializer_class = CurriculumUnitSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def perform_create(self, serializer):
        data = serializer.validated_data
        self.instance = CurriculumService().create_unit(**data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(self.instance).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        self.instance = CurriculumService().update_unit(serializer.instance, **serializer.validated_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(self.get_serializer(self.instance).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        unit = CurriculumService().archive_unit(self.get_object())
        return Response(self.get_serializer(unit).data)


class LearningResourceViewSet(viewsets.ModelViewSet):
    serializer_class = LearningResourceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        institution_ids = list(
            InstitutionMembership.objects.filter(user=self.request.user, is_active=True).values_list("institution_id", flat=True)
        )
        queryset = LearningResource.objects.exclude(status=LearningResource.Status.ARCHIVED).order_by("-created_at")
        if not institution_ids:
            return queryset.none()
        queryset = queryset.filter(subject__institution_id__in=institution_ids)
        subject_id = self.request.query_params.get("subject")
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        return queryset

    def perform_create(self, serializer):
        data = serializer.validated_data
        self.instance = LearningResourceService().create_resource(**data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(self.instance).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        self.instance = LearningResourceService().update_resource(serializer.instance, **serializer.validated_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(self.get_serializer(self.instance).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        resource = LearningResourceService().archive_resource(self.get_object())
        return Response(self.get_serializer(resource).data)

    @action(detail=True, methods=["get"], url_path="teaching-readiness")
    def teaching_readiness(self, request, pk=None):
        from apps.content_processing.models import TeachingReadinessEvaluation

        resource = self.get_object()
        evaluation = TeachingReadinessEvaluation.objects.filter(resource=resource).order_by("-evaluated_at").first()
        if evaluation is None:
            return Response({
                "resource_id": str(resource.id), "status": "not_ready",
                "latest_evaluation_id": None, "decision": None, "blockers": [], "warnings": [],
                "can_evaluate": bool(request.user.is_staff), "can_reevaluate": False,
            })
        blockers = [item for item in evaluation.checks if not item["passed"] and item["severity"] == "blocker"]
        warnings = [item for item in evaluation.checks if not item["passed"] and item["severity"] == "warning"]
        return Response({
            "resource_id": str(resource.id),
            "status": "stale" if evaluation.invalidated_at else ("ready_for_teaching" if evaluation.decision == "ready" else "not_ready"),
            "latest_evaluation_id": str(evaluation.id), "decision": evaluation.decision,
            "lineage_fingerprint": evaluation.lineage_fingerprint, "policy_version": evaluation.policy_version,
            "checks_passed": evaluation.checks_passed, "checks_failed": evaluation.checks_failed,
            "blocker_count": evaluation.blocker_count, "warning_count": evaluation.warning_count,
            "blockers": blockers, "warnings": warnings, "can_evaluate": bool(request.user.is_staff),
            "can_reevaluate": bool(request.user.is_staff),
        })

    @action(detail=True, methods=["post"], url_path="teaching-readiness/evaluate")
    def evaluate_teaching_readiness(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from apps.content_processing.api.serializers import TeachingReadinessEvaluationSerializer
        from apps.content_processing.application.teaching_readiness_services import EvaluateTeachingReadinessService

        resource = self.get_object()
        try:
            evaluation, replayed = EvaluateTeachingReadinessService().execute(
                resource_id=resource.id, idempotency_key=request.data.get("idempotency_key", ""),
                expected_lineage_fingerprint=request.data.get("expected_lineage_fingerprint", ""),
                reason=request.data.get("reason", ""), actor=request.user,
            )
        except DjangoValidationError as exc:
            details = getattr(exc, "messages", [str(exc)])
            code = status.HTTP_409_CONFLICT if any("CONFLICT" in item for item in details) else status.HTTP_422_UNPROCESSABLE_ENTITY
            return Response({"errors": details}, status=code)
        return Response(
            TeachingReadinessEvaluationSerializer(evaluation).data,
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class ContentSectionViewSet(viewsets.ModelViewSet):
    serializer_class = ContentSectionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        institution_ids = list(
            InstitutionMembership.objects.filter(user=self.request.user, is_active=True).values_list("institution_id", flat=True)
        )
        queryset = ContentSection.objects.all().order_by("learning_resource", "sequence_number")
        if not institution_ids:
            return queryset.none()
        queryset = queryset.filter(learning_resource__subject__institution_id__in=institution_ids)
        learning_resource_id = self.request.query_params.get("learning_resource")
        if learning_resource_id:
            queryset = queryset.filter(learning_resource_id=learning_resource_id)
        return queryset

    def perform_create(self, serializer):
        data = serializer.validated_data
        self.instance = ManualAuthoringService().create_section(**data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(self.instance).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        self.instance = ManualAuthoringService().update_section(serializer.instance, **serializer.validated_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(self.get_serializer(self.instance).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        section = ManualAuthoringService().archive_section(self.get_object())
        return Response(self.get_serializer(section).data)

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    def submit_for_review(self, request, pk=None):
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = ContentReviewService().submit_section_for_review(
            self.get_object(),
            submitted_by=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response(self.get_serializer(section).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = ContentReviewService().approve_section(
            self.get_object(),
            approved_by=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response(self.get_serializer(section).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = ContentReviewService().reject_section(
            self.get_object(),
            rejected_by=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response(self.get_serializer(section).data)

    @action(detail=True, methods=["post"], url_path="mark-quality")
    def mark_quality(self, request, pk=None):
        serializer = QualityMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = ContentReviewService().mark_section_quality(
            self.get_object(),
            serializer.validated_data["quality_status"],
            marked_by=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response(self.get_serializer(section).data)


class ContentConceptViewSet(viewsets.ModelViewSet):
    serializer_class = ContentConceptSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        institution_ids = list(
            InstitutionMembership.objects.filter(user=self.request.user, is_active=True).values_list("institution_id", flat=True)
        )
        queryset = ContentConcept.objects.all().order_by("content_section", "sequence_number")
        if not institution_ids:
            return queryset.none()
        queryset = queryset.filter(content_section__learning_resource__subject__institution_id__in=institution_ids)
        learning_resource_id = self.request.query_params.get("learning_resource")
        if learning_resource_id:
            queryset = queryset.filter(content_section__learning_resource_id=learning_resource_id)
        content_section_id = self.request.query_params.get("content_section")
        if content_section_id:
            queryset = queryset.filter(content_section_id=content_section_id)
        return queryset

    def perform_create(self, serializer):
        data = serializer.validated_data
        self.instance = ManualAuthoringService().create_concept(**data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(self.instance).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        self.instance = ManualAuthoringService().update_concept(serializer.instance, **serializer.validated_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(self.get_serializer(self.instance).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        concept = ManualAuthoringService().archive_concept(self.get_object())
        return Response(self.get_serializer(concept).data)

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    def submit_for_review(self, request, pk=None):
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concept = ContentReviewService().submit_concept_for_review(
            self.get_object(),
            submitted_by=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response(self.get_serializer(concept).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concept = ContentReviewService().approve_concept(
            self.get_object(),
            approved_by=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response(self.get_serializer(concept).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concept = ContentReviewService().reject_concept(
            self.get_object(),
            rejected_by=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response(self.get_serializer(concept).data)

    @action(detail=True, methods=["post"], url_path="mark-quality")
    def mark_quality(self, request, pk=None):
        serializer = QualityMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concept = ContentReviewService().mark_concept_quality(
            self.get_object(),
            serializer.validated_data["quality_status"],
            marked_by=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response(self.get_serializer(concept).data)


class ResourceIngestionJobViewSet(viewsets.ModelViewSet):
    queryset = ResourceIngestionJob.objects.all().order_by("-created_at")
    serializer_class = ResourceIngestionJobSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        data = serializer.validated_data
        self.instance = ResourceIngestionService().create_job(requested_by=self.request.user, **data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(self.instance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        job = ResourceIngestionService().start_job(self.get_object())
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        job = ResourceIngestionService().complete_job(self.get_object())
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"])
    def fail(self, request, pk=None):
        serializer = IngestionFailureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = ResourceIngestionService().fail_job(
            self.get_object(),
            serializer.validated_data["error_message"],
        )
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        job = ResourceIngestionService().cancel_job(self.get_object())
        return Response(self.get_serializer(job).data)
