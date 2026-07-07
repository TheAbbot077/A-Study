from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all().order_by("code")
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def perform_create(self, serializer):
        data = serializer.validated_data
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
    queryset = LearningResource.objects.all().order_by("-created_at")
    serializer_class = LearningResourceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

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


class ContentSectionViewSet(viewsets.ModelViewSet):
    queryset = ContentSection.objects.all().order_by("learning_resource", "sequence_number")
    serializer_class = ContentSectionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

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
    queryset = ContentConcept.objects.all().order_by("content_section", "sequence_number")
    serializer_class = ContentConceptSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

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
