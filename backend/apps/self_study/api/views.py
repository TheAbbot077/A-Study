from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import InstitutionRole

from ..application.services import (
    ActivateSelfStudyIntentService,
    AuthorizeAutonomousCurriculumFallbackService,
    AuthorizeResourceAcquisitionService,
    CancelSelfStudyIntentService,
    CreateSelfStudyIntentService,
    MarkSelfStudyIntentReadyService,
    ReturnSelfStudyIntentToDraftService,
    SupersedeSelfStudyIntentService,
    UpdateSelfStudyIntentService,
)
from ..application.curriculum_services import StartCurriculumResolutionService
from ..application.diagnostic_services import CreateEntryDiagnosticService
from ..application.evidence_services import CreateEvidenceMappingRunService
from ..curriculum_models import CurriculumResolutionAttempt
from ..models import LearningPolicyRuleSet, SelfStudyIntent
from .serializers import (
    AcquisitionCandidateSerializer,
    CreateIntentSerializer,
    FallbackAuthorizationSerializer,
    PolicyPreferenceSerializer,
    PublicPolicySerializer,
    SelfStudyIntentSerializer,
    UpdateIntentSerializer,
    VersionCommandSerializer,
)
from .curriculum_serializers import StartResolutionSerializer, resolution_payload
from .diagnostic_serializers import CreateDiagnosticSerializer, PublicDiagnosticSerializer
from .evidence_serializers import CreateMappingRunSerializer,MappingRunSerializer


def problem(exc: DjangoValidationError):
    code = getattr(exc, "code", None)
    if not code and hasattr(exc, "error_list") and exc.error_list:
        code = getattr(exc.error_list[0], "code", None)
    code = (code or "SELF_STUDY_VALIDATION_FAILED").upper()
    messages = getattr(exc, "messages", None) or [str(exc)]
    response_status = status.HTTP_409_CONFLICT if code in {
        "INTENT_VERSION_CONFLICT",
        "WORKSPACE_VERSION_CONFLICT",
        "INVALID_INTENT_TRANSITION",
        "INTENT_NOT_EDITABLE",
    } else status.HTTP_422_UNPROCESSABLE_ENTITY
    return Response({"code": code, "detail": messages[0], "blockers": messages}, status=response_status)


class SelfStudyIntentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _queryset(self, request):
        query = SelfStudyIntent.objects.select_related(
            "learner", "tenant", "subject", "effective_policy_snapshot"
        )
        if request.user.is_superuser:
            return query
        tenant_ids = request.user.institutionmembership_set.filter(
            is_active=True,
            role__in=[
                InstitutionRole.ADMINISTRATOR,
                InstitutionRole.INSTITUTION_OWNER,
                InstitutionRole.SYSTEM_ADMINISTRATOR,
            ],
        ).values_list("institution_id", flat=True)
        return query.filter(Q(learner=request.user) | Q(tenant_id__in=tenant_ids)).distinct()

    def _intent(self, request, pk):
        try:
            return self._queryset(request).get(pk=pk)
        except SelfStudyIntent.DoesNotExist as exc:
            # Do not confirm whether a cross-tenant identifier exists.
            raise NotFound("SELF_STUDY_INTENT_NOT_FOUND") from exc

    def list(self, request):
        return Response(SelfStudyIntentSerializer(self._queryset(request).order_by("-created_at"), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(SelfStudyIntentSerializer(self._intent(request, pk)).data)

    def create(self, request):
        serializer = CreateIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        acknowledged = data.pop("policy_acknowledged")
        data["policy_acknowledged_at"] = timezone.now() if acknowledged else None
        data.setdefault("learner", request.user)
        try:
            intent = CreateSelfStudyIntentService().execute(actor=request.user, **data)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(SelfStudyIntentSerializer(intent).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        self._intent(request, pk)
        serializer = UpdateIntentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version", None)
        if expected_version is None:
            return Response(
                {"code": "INTENT_VERSION_CONFLICT", "detail": "expected_version is required."},
                status=status.HTTP_409_CONFLICT,
            )
        if "policy_acknowledged" in data:
            data["policy_acknowledged_at"] = timezone.now() if data.pop("policy_acknowledged") else None
        try:
            intent = UpdateSelfStudyIntentService().execute(
                intent_id=pk,
                actor=request.user,
                expected_version=expected_version,
                changes=data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(SelfStudyIntentSerializer(intent).data)

    def _version_command(self, request, pk, service):
        self._intent(request, pk)
        serializer = VersionCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            intent = service.execute(
                intent_id=pk,
                actor=request.user,
                expected_version=serializer.validated_data["expected_version"],
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(SelfStudyIntentSerializer(intent).data)

    @action(detail=True, methods=["post"])
    def ready(self, request, pk=None):
        return self._version_command(request, pk, MarkSelfStudyIntentReadyService())

    @action(detail=True, methods=["post"])
    def draft(self, request, pk=None):
        return self._version_command(request, pk, ReturnSelfStudyIntentToDraftService())

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._version_command(request, pk, ActivateSelfStudyIntentService())

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._version_command(request, pk, CancelSelfStudyIntentService())

    @action(detail=True, methods=["post"])
    def supersede(self, request, pk=None):
        return self._version_command(request, pk, SupersedeSelfStudyIntentService())

    @action(detail=True, methods=["get"])
    def policy(self, request, pk=None):
        intent = self._intent(request, pk)
        if not intent.effective_policy_snapshot_id:
            return Response(
                {"code": "POLICY_SNAPSHOT_REQUIRED", "detail": "The intent has no active policy snapshot."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(PublicPolicySerializer(intent.effective_policy_snapshot).data)

    @action(detail=True, methods=["get", "post"], url_path="entry-diagnostic")
    def entry_diagnostic(self, request, pk=None):
        intent=self._intent(request,pk)
        if request.method=="GET":
            diagnostic=intent.entry_diagnostics.order_by("-created_at").first()
            return Response(PublicDiagnosticSerializer(diagnostic).data if diagnostic else {"status":"NOT_CREATED"})
        serializer=CreateDiagnosticSerializer(data=request.data);serializer.is_valid(raise_exception=True)
        try:diagnostic,replayed=CreateEntryDiagnosticService().execute(intent_id=intent.id,actor=request.user,purpose_acknowledged=serializer.validated_data["purpose_acknowledged"])
        except DjangoPermissionDenied as exc:raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:return problem(exc)
        return Response(PublicDiagnosticSerializer(diagnostic).data,status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED)

    @action(detail=True,methods=["get","post"],url_path="evidence-mappings")
    def evidence_mappings(self,request,pk=None):
        intent=self._intent(request,pk)
        if request.method=="GET":return Response(MappingRunSerializer(intent.evidence_mapping_runs.order_by("-created_at"),many=True).data)
        serializer=CreateMappingRunSerializer(data=request.data);serializer.is_valid(raise_exception=True)
        try:run,replayed=CreateEvidenceMappingRunService().execute(intent_id=intent.id,resource_ids=serializer.validated_data["resource_ids"],actor=request.user)
        except DjangoPermissionDenied as exc:raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:return problem(exc)
        return Response(MappingRunSerializer(run).data,status=status.HTTP_200_OK if replayed else status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["patch"])
    @transaction.atomic
    def preferences(self, request, pk=None):
        intent = self._intent(request, pk)
        if request.user.id != intent.learner_id:
            raise PermissionDenied("SELF_STUDY_INTENT_ACCESS_DENIED")
        if intent.status not in {"DRAFT", "READY"}:
            return Response(
                {"code": "INTENT_NOT_EDITABLE", "detail": "Active policy snapshots cannot be changed."},
                status=status.HTTP_409_CONFLICT,
            )
        current = LearningPolicyRuleSet.objects.filter(
            authority=LearningPolicyRuleSet.Authority.LEARNER,
            tenant=intent.tenant,
            learner=intent.learner,
            is_active=True,
        ).order_by("-version").first()
        serializer = PolicyPreferenceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        policy_fields = list(PolicyPreferenceSerializer.Meta.fields)
        baseline = current or LearningPolicyRuleSet()
        values = {field: getattr(baseline, field) for field in policy_fields}
        values.update(serializer.validated_data)
        version = (current.version + 1) if current else 1
        if current:
            current.is_active = False
            current.save(update_fields=["is_active", "updated_at"])
        policy = LearningPolicyRuleSet(
            authority=LearningPolicyRuleSet.Authority.LEARNER,
            tenant=intent.tenant,
            learner=intent.learner,
            version=version,
            **values,
        )
        try:
            policy.full_clean()
            policy.save()
        except DjangoValidationError as exc:
            return problem(exc)
        transaction.on_commit(
            lambda: EventPublisher().publish(
                BusinessEvent.create(
                    "self_study.resource_acquisition_preference_changed",
                    payload={
                        "intent_id": str(intent.id),
                        "policy_id": str(policy.id),
                        "version": policy.version,
                    },
                )
            )
        )
        return Response(PolicyPreferenceSerializer(policy).data)

    @action(detail=True, methods=["post"], url_path="authorize-resource")
    def authorize_resource(self, request, pk=None):
        self._intent(request, pk)
        serializer = AcquisitionCandidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decision = AuthorizeResourceAcquisitionService().execute(
                intent_id=pk,
                actor=request.user,
                candidate=serializer.candidate(),
                idempotency_key=serializer.validated_data["idempotency_key"],
                canonical_uri=serializer.validated_data.get("canonical_uri", ""),
            )
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(
            {
                "id": decision.id,
                "policy_snapshot_id": decision.policy_snapshot_id,
                "decision": decision.decision,
                "reason_codes": decision.reason_codes,
                "created_at": decision.created_at,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="authorize-autonomous-fallback")
    def authorize_autonomous_fallback(self, request, pk=None):
        self._intent(request, pk)
        serializer = FallbackAuthorizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decision = AuthorizeAutonomousCurriculumFallbackService().execute(
                intent_id=pk,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(
            {
                "id": decision.id,
                "policy_snapshot_id": decision.policy_snapshot_id,
                "authorized": decision.authorized,
                "reason_codes": decision.reason_codes,
                "created_at": decision.created_at,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"], url_path="curriculum-resolution")
    def curriculum_resolution(self, request, pk=None):
        intent = self._intent(request, pk)
        if request.method == "GET":
            attempt = CurriculumResolutionAttempt.objects.filter(intent=intent).order_by("-created_at").first()
            if attempt is None:
                return Response(
                    {"code": "CURRICULUM_RESOLUTION_FAILED", "detail": "No curriculum resolution exists."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(resolution_payload(attempt))
        serializer = StartResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attempt, replayed = StartCurriculumResolutionService().execute(
                intent_id=pk, actor=request.user, **serializer.validated_data
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(
            resolution_payload(attempt),
            status=status.HTTP_200_OK if replayed else status.HTTP_202_ACCEPTED,
        )
