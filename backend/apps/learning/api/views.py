from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academic.domain.models import ContentConcept, LearningResource
from apps.learning.api.serializers import (
    AbbotTeachingResponseSerializer,
    AskQuestionSerializer,
    ConceptBrowserStateSerializer,
    LearningConversationStateSerializer,
    PedagogicalSessionSerializer,
    StartOrResumeConceptSerializer,
)
from apps.learning.domain.models import PedagogicalSession
from apps.learning.services import AbbotTeachingAgentService, ConceptBrowserService, ConversationOrchestratorService
from apps.users.domain.models import InstitutionMembership


class PedagogicalSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PedagogicalSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = PedagogicalSession.objects.filter(learner=self.request.user).select_related("content_concept").order_by("-created_at")
        content_concept_id = self.request.query_params.get("content_concept")
        if content_concept_id:
            queryset = queryset.filter(content_concept_id=content_concept_id)
        return queryset

    @action(detail=False, methods=["get"], url_path="concept-browser")
    def concept_browser(self, request):
        learning_resource_id = request.query_params.get("learning_resource")
        if not learning_resource_id:
            raise ValidationError({"learning_resource": "This query parameter is required."})

        institution_ids = list(
            InstitutionMembership.objects.filter(user=request.user, is_active=True).values_list("institution_id", flat=True)
        )
        resource = LearningResource.objects.filter(
            id=learning_resource_id,
            subject__institution_id__in=institution_ids,
        ).first()
        if resource is None:
            raise ValidationError({"learning_resource": "Resource not found or unavailable."})

        states = ConceptBrowserService().list_resource_concept_states(request.user, resource)
        return Response(ConceptBrowserStateSerializer(states, many=True).data)

    @action(detail=False, methods=["post"], url_path="start-or-resume")
    def start_or_resume(self, request):
        serializer = StartOrResumeConceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        institution_ids = list(
            InstitutionMembership.objects.filter(user=request.user, is_active=True).values_list("institution_id", flat=True)
        )
        concept = (
            ContentConcept.objects.filter(
                id=serializer.validated_data["content_concept"].id,
                content_section__learning_resource__subject__institution_id__in=institution_ids,
            )
            .select_related("content_section", "content_section__learning_resource")
            .first()
        )
        if concept is None:
            raise ValidationError({"content_concept": "Concept not found or unavailable."})

        try:
            session = ConceptBrowserService().start_or_resume_concept(request.user, concept)
        except ValueError as exc:
            raise ValidationError({"content_concept": str(exc)}) from exc

        return Response(PedagogicalSessionSerializer(session).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="conversation")
    def conversation(self, request, pk=None):
        session = self.get_object()
        orchestrator = ConversationOrchestratorService()
        turns = orchestrator.list_conversation_turns(session)
        payload = {
            "session": session,
            "turns": turns,
            "next_expected_interaction": orchestrator.next_expected_interaction(session),
            "streaming_supported": False,
        }
        return Response(LearningConversationStateSerializer(payload).data)

    @action(detail=True, methods=["post"], url_path="teach")
    def teach(self, request, pk=None):
        session = self.get_object()
        orchestrator = ConversationOrchestratorService()
        if not orchestrator.list_conversation_turns(session):
            orchestrator.initialize_conversation(session)
        response = AbbotTeachingAgentService().generate_teaching_response(session)
        return Response(
            {
                "response": AbbotTeachingResponseSerializer(response).data,
                "conversation": LearningConversationStateSerializer(
                    {
                        "session": session,
                        "turns": orchestrator.list_conversation_turns(session),
                        "next_expected_interaction": orchestrator.next_expected_interaction(session),
                        "streaming_supported": False,
                    }
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="ask")
    def ask(self, request, pk=None):
        session = self.get_object()
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        orchestrator = ConversationOrchestratorService()
        if not orchestrator.list_conversation_turns(session):
            orchestrator.initialize_conversation(session)
        orchestrator.add_turn(
            session=session,
            sender_type="learner",
            message_type="learner_question",
            content=serializer.validated_data["question"],
        )
        response = AbbotTeachingAgentService().generate_clarification_response(
            session,
            serializer.validated_data["question"],
        )
        return Response(
            {
                "response": AbbotTeachingResponseSerializer(response).data,
                "conversation": LearningConversationStateSerializer(
                    {
                        "session": session,
                        "turns": orchestrator.list_conversation_turns(session),
                        "next_expected_interaction": orchestrator.next_expected_interaction(session),
                        "streaming_supported": False,
                    }
                ).data,
            },
            status=status.HTTP_200_OK,
        )
