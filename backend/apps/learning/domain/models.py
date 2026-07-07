import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.academic.domain.models import ContentConcept


class PedagogicalState(models.TextChoices):
    CREATED = "created", "Created"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    ABANDONED = "abandoned", "Abandoned"


class PedagogicalSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pedagogical_sessions")
    content_concept = models.ForeignKey(ContentConcept, on_delete=models.CASCADE, related_name="pedagogical_sessions")
    status = models.CharField(max_length=50, choices=PedagogicalState.choices, default=PedagogicalState.CREATED)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "learning_pedagogical_session"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["learner"], name="learn_session_learner_idx"),
            models.Index(fields=["content_concept"], name="learn_session_concept_idx"),
            models.Index(fields=["status"], name="learn_session_status_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.learner_id} :: {self.content_concept_id} [{self.status}]"


class PedagogicalMessage(models.Model):
    class SenderType(models.TextChoices):
        LEARNER = "learner", "Learner"
        ABBOT = "abbot", "Abbot"
        ARIEL = "ariel", "Ariel"
        SYSTEM = "system", "System"

    class MessageType(models.TextChoices):
        EXPLANATION = "explanation", "Explanation"
        QUESTION = "question", "Question"
        RESPONSE = "response", "Response"
        CLARIFICATION = "clarification", "Clarification"
        SUMMARY = "summary", "Summary"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedagogical_session = models.ForeignKey(PedagogicalSession, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=50, choices=SenderType.choices)
    message_type = models.CharField(max_length=50, choices=MessageType.choices)
    content = models.TextField()
    sequence_number = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "learning_pedagogical_message"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["pedagogical_session", "sequence_number"], name="unique_pedagogical_session_sequence"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="pedagogical_message_sequence_gte_1"),
        ]
        indexes = [
            models.Index(fields=["pedagogical_session"], name="learn_msg_session_idx"),
            models.Index(fields=["sender_type"], name="learn_msg_sender_idx"),
            models.Index(fields=["message_type"], name="learn_msg_type_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.pedagogical_session_id} #{self.sequence_number}"


__all__ = ["PedagogicalState", "PedagogicalSession", "PedagogicalMessage"]
