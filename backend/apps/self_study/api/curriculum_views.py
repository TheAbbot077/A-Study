from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.curriculum_services import (
    CompositeCurriculumDecisionService,
    ConfirmCurriculumSelectionService,
    CurriculumRegistryService,
)
from ..application.graph_services import StartCurriculumGraphBuildService
from ..graph_models import ConstructionMethod
from ..curriculum_models import (
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionAttempt,
    CurriculumVersion,
    CurriculumVersionStatus,
    RegistryStatus,
    VerificationStatus,
)
from .curriculum_serializers import (
    CreateCurriculumVersionSerializer,
    CurriculumAuthoritySerializer,
    CurriculumReferenceSerializer,
    CurriculumVersionSerializer,
    SupersedeCurriculumVersionSerializer,
    ConfirmCurriculumSelectionSerializer,
    resolution_payload,
)
from .graph_serializers import GraphBuildSerializer, GraphSerializer
from .views import problem


def _tenant_ids(user):
    return user.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)


class PublicCurriculumViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CurriculumReferenceSerializer

    def get_queryset(self):
        tenant_ids = _tenant_ids(self.request.user)
        return CurriculumReference.objects.select_related("authority", "current_version").filter(
            Q(tenant__isnull=True) | Q(tenant_id__in=tenant_ids),
            status=RegistryStatus.ACTIVE,
            authority__verification_status=VerificationStatus.VERIFIED,
            authority__status=RegistryStatus.ACTIVE,
            current_version__status=CurriculumVersionStatus.ACTIVE,
        ).order_by("title")

    @action(detail=True, methods=["get"], url_path=r"versions/(?P<version_id>[^/.]+)")
    def version(self, request, pk=None, version_id=None):
        reference = self.get_object()
        try:
            version = reference.versions.get(id=version_id)
        except CurriculumVersion.DoesNotExist as exc:
            raise NotFound() from exc
        return Response(CurriculumVersionSerializer(version).data)


class CurriculumAuthorityGovernanceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = CurriculumAuthoritySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            authority = CurriculumRegistryService().create_authority(actor=request.user, **serializer.validated_data)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(CurriculumAuthoritySerializer(authority).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        try:
            authority = CurriculumRegistryService().verify_authority(pk, request.user)
        except CurriculumAuthority.DoesNotExist as exc:
            raise NotFound() from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(CurriculumAuthoritySerializer(authority).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        try:
            authority = CurriculumRegistryService().suspend_authority(pk, request.user)
        except CurriculumAuthority.DoesNotExist as exc:
            raise NotFound() from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(CurriculumAuthoritySerializer(authority).data)


class CurriculumReferenceGovernanceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = CurriculumReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reference = CurriculumRegistryService().create_reference(actor=request.user, **serializer.validated_data)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(CurriculumReferenceSerializer(reference).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def versions(self, request, pk=None):
        serializer = CreateCurriculumVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = CurriculumRegistryService().create_version(
                reference_id=pk, actor=request.user, **serializer.validated_data
            )
        except CurriculumReference.DoesNotExist as exc:
            raise NotFound() from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(CurriculumVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class CurriculumVersionGovernanceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        try:
            version = CurriculumRegistryService().activate_version(pk, request.user)
        except CurriculumVersion.DoesNotExist as exc:
            raise NotFound() from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(CurriculumVersionSerializer(version).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        try:
            version = CurriculumRegistryService().suspend_version(pk, request.user)
        except CurriculumVersion.DoesNotExist as exc:
            raise NotFound() from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(CurriculumVersionSerializer(version).data)

    @action(detail=True, methods=["post"])
    def supersede(self, request, pk=None):
        serializer = SupersedeCurriculumVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = CurriculumRegistryService().supersede_version(
                pk, serializer.validated_data["replacement_version_id"], request.user
            )
        except CurriculumVersion.DoesNotExist as exc:
            raise NotFound() from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(CurriculumVersionSerializer(version).data)


class CurriculumResolutionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _attempt(self, request, pk):
        tenant_ids = _tenant_ids(request.user)
        query = CurriculumResolutionAttempt.objects.select_related(
            "intent", "selection", "composite_proposal", "resolution_failure"
        ).filter(Q(intent__learner=request.user) | Q(intent__tenant_id__in=tenant_ids))
        try:
            return query.get(id=pk)
        except CurriculumResolutionAttempt.DoesNotExist as exc:
            raise NotFound() from exc

    def retrieve(self, request, pk=None):
        return Response(resolution_payload(self._attempt(request, pk)))

    @action(detail=True, methods=["post"], url_path="build-graph")
    def build_graph(self, request, pk=None):
        self._attempt(request, pk)
        serializer = GraphBuildSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            graph, _, replayed = StartCurriculumGraphBuildService().execute(
                attempt_id=pk,
                actor=request.user,
                construction_method=serializer.validated_data["construction_method"],
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        payload = GraphSerializer(graph).data
        payload["replayed"] = replayed
        return Response(payload, status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        self._attempt(request, pk)
        serializer = ConfirmCurriculumSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decision = ConfirmCurriculumSelectionService().execute(
                attempt_id=pk, actor=request.user, **serializer.validated_data
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(
            {
                "id": decision.id,
                "curriculum_version_id": decision.curriculum_version_id,
                "decision_type": decision.decision_type,
            }
        )

    @action(detail=True, methods=["post"], url_path="composite/approve")
    def approve_composite(self, request, pk=None):
        self._attempt(request, pk)
        try:
            proposal = CompositeCurriculumDecisionService().execute(attempt_id=pk, actor=request.user, approve=True)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response({"id": proposal.id, "status": proposal.status})

    @action(detail=True, methods=["post"], url_path="composite/reject")
    def reject_composite(self, request, pk=None):
        self._attempt(request, pk)
        try:
            proposal = CompositeCurriculumDecisionService().execute(attempt_id=pk, actor=request.user, approve=False)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response({"id": proposal.id, "status": proposal.status})
