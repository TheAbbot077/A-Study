from django.urls import path

from .views import (
    LearnerPreparednessAssignmentParticipantRemoveView,
    LearnerPreparednessArielOptInView,
    LearnerPreparednessParticipationView,
    LearnerPreparednessRespondView,
    LessonPreparationListCreateView,
    PreparednessActivityCreateView,
    PreparednessAssignmentCreateView,
    PreparednessAssignmentParticipantCreateView,
    PreparednessProjectionView,
)

urlpatterns = [
    path("lesson-preparations/", LessonPreparationListCreateView.as_view(), name="lesson-preparation-list"),
    path("lesson-preparations/<uuid:lesson_preparation_id>/activities/", PreparednessActivityCreateView.as_view(), name="preparedness-activity-create"),
    path("lesson-preparations/<uuid:lesson_preparation_id>/assignments/", PreparednessAssignmentCreateView.as_view(), name="preparedness-assignment-create"),
    path("assignments/<uuid:assignment_id>/projection/", PreparednessProjectionView.as_view(), name="preparedness-projection"),
    path("assignments/<uuid:assignment_id>/participants/", PreparednessAssignmentParticipantCreateView.as_view(), name="preparedness-assignment-participant-create"),
    path("assignments/<uuid:assignment_id>/participants/<uuid:participation_id>/", LearnerPreparednessAssignmentParticipantRemoveView.as_view(), name="preparedness-assignment-participant-remove"),
    path("assignments/<uuid:assignment_id>/participation/", LearnerPreparednessParticipationView.as_view(), name="preparedness-participation"),
    path("participations/<uuid:participation_id>/respond/", LearnerPreparednessRespondView.as_view(), name="preparedness-respond"),
    path("participations/<uuid:participation_id>/ariel-opt-in/", LearnerPreparednessArielOptInView.as_view(), name="preparedness-ariel-opt-in"),
]
