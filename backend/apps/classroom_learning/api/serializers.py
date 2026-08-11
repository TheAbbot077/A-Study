from rest_framework import serializers

from ..domain.models import (
    ClassPreparednessAssignment,
    LessonPreparation,
    LearnerPreparednessParticipation,
    PreparednessActivity,
)


class LessonPreparationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonPreparation
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "published_at", "completed_at", "cancelled_at", "archived_at", "version")


class PreparednessActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PreparednessActivity
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "version")


class ClassPreparednessAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassPreparednessAssignment
        fields = "__all__"
        read_only_fields = ("id", "published_at", "closed_at", "cancelled_at", "version")


class LearnerPreparednessParticipationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearnerPreparednessParticipation
        fields = "__all__"
        read_only_fields = ("id", "started_at", "responded_at", "ariel_opted_in_at", "completed_at", "version")
