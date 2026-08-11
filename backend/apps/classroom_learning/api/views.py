from rest_framework import generics, permissions, response, status, views
from django.shortcuts import get_object_or_404

from ..application.services import (
    AddLearnerPreparednessParticipantService,
    AssignPreparednessService,
    BuildClassPreparednessProjectionService,
    CreateLessonPreparationService,
    OpenPreparednessAssignmentService,
    OptInArielPreparednessService,
    RemoveLearnerPreparednessParticipantService,
    PublishPreparednessActivityService,
    RespondToPreparednessService,
    StartLearnerPreparednessService,
)
from ..domain.models import (
    ClassPreparednessAssignment,
    LessonPreparation,
    LearnerPreparednessParticipation,
    PreparednessActivity,
)
from .serializers import (
    ClassPreparednessAssignmentSerializer,
    LessonPreparationSerializer,
    LearnerPreparednessParticipationSerializer,
    PreparednessActivitySerializer,
)


class LessonPreparationListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LessonPreparationSerializer
    queryset = LessonPreparation.objects.all()

    def perform_create(self, serializer):
        serializer.save()


class PreparednessActivityCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PreparednessActivitySerializer
    queryset = PreparednessActivity.objects.all()


class PreparednessAssignmentCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lesson_preparation_id):
        lesson = get_object_or_404(LessonPreparation, pk=lesson_preparation_id)
        activity = PreparednessActivity.objects.filter(lesson_preparation=lesson).order_by("created_at").first()
        if activity is None:
            return response.Response({"detail": "No preparedness activity available"}, status=status.HTTP_400_BAD_REQUEST)
        assignment = AssignPreparednessService.execute(
            activity=activity,
            class_group=lesson.class_group,
            course_offering=lesson.course_offering,
            institution=lesson.institution,
            population_mode=request.data.get("population_mode", "explicit_participants"),
        )
        return response.Response(ClassPreparednessAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class PreparednessProjectionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, assignment_id):
        assignment = get_object_or_404(ClassPreparednessAssignment, pk=assignment_id)
        projection = BuildClassPreparednessProjectionService.execute(assignment=assignment)
        return response.Response(projection)


class PreparednessAssignmentParticipantCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, assignment_id):
        assignment = get_object_or_404(ClassPreparednessAssignment, pk=assignment_id)
        learner_id = request.data.get("learner_id")
        if learner_id is None:
            return response.Response({"detail": "learner_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        participation, created = AddLearnerPreparednessParticipantService.execute(assignment=assignment, learner_id=learner_id)
        payload = LearnerPreparednessParticipationSerializer(participation).data
        payload["created"] = created
        return response.Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class LearnerPreparednessAssignmentParticipantRemoveView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, assignment_id, participation_id):
        assignment = get_object_or_404(ClassPreparednessAssignment, pk=assignment_id)
        participation = get_object_or_404(LearnerPreparednessParticipation, pk=participation_id, assignment=assignment)
        participation = RemoveLearnerPreparednessParticipantService.execute(participation=participation)
        return response.Response(LearnerPreparednessParticipationSerializer(participation).data)


class LearnerPreparednessParticipationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, assignment_id):
        assignment = get_object_or_404(ClassPreparednessAssignment, pk=assignment_id)
        participation = StartLearnerPreparednessService.execute(assignment=assignment, learner=request.user)
        return response.Response(LearnerPreparednessParticipationSerializer(participation).data, status=status.HTTP_201_CREATED)


class LearnerPreparednessRespondView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, participation_id):
        participation = get_object_or_404(LearnerPreparednessParticipation, pk=participation_id)
        participation, _ = RespondToPreparednessService.execute(
            participation=participation,
            learner_id=request.user.id,
            response_text=request.data.get("response_text", ""),
        )
        return response.Response(LearnerPreparednessParticipationSerializer(participation).data)


class LearnerPreparednessArielOptInView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, participation_id):
        participation = get_object_or_404(LearnerPreparednessParticipation, pk=participation_id)
        participation = OptInArielPreparednessService.execute(participation=participation, learner_id=request.user.id)
        return response.Response(LearnerPreparednessParticipationSerializer(participation).data)
