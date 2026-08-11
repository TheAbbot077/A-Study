from django.db import models


class LessonPreparationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY = "ready", "Ready"
    PUBLISHED = "published", "Published"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class PreparednessActivityStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"
    ARCHIVED = "archived", "Archived"


class PreparednessPromptType(models.TextChoices):
    EXPLANATION = "explanation", "Explanation"
    EXAMPLE = "example", "Example"
    COMPARISON = "comparison", "Comparison"
    DIAGRAM = "diagram", "Diagram"
    WHAT_IF = "what_if", "What If"
    SHORT_APPLICATION = "short_application", "Short Application"
    ARIEL_ATTEMPT = "ariel_attempt", "Ariel Attempt"


class PrerequisitePriority(models.TextChoices):
    REQUIRED = "required", "Required"
    IMPORTANT = "important", "Important"
    HELPFUL = "helpful", "Helpful"


class ParticipationStatus(models.TextChoices):
    ASSIGNED = "assigned", "Assigned"
    OPEN = "open", "Open"
    STARTED = "started", "Started"
    RESPONDED = "responded", "Responded"
    COMPLETED = "completed", "Completed"
    DECLINED = "declined", "Declined"
    EXPIRED = "expired", "Expired"


class ArielPreparednessAttemptStatus(models.TextChoices):
    CREATED = "created", "Created"
    READY = "ready", "Ready"
    ATTEMPTED = "attempted", "Attempted"
    COMPLETED = "completed", "Completed"
    INSUFFICIENT_MEMORY = "insufficient_memory", "Insufficient Memory"
    CONFLICTED_MEMORY = "conflicted_memory", "Conflicted Memory"
    EXCLUDED = "excluded", "Excluded"
    FAILED = "failed", "Failed"


class PreparednessAssignmentPopulationMode(models.TextChoices):
    EXPLICIT_PARTICIPANTS = "explicit_participants", "Explicit Participants"
    CLASS_ROSTER = "class_roster", "Class Roster"
