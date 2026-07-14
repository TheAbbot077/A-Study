import uuid

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.academic.domain.models import ContentConcept


@dataclass(frozen=True)
class AssessmentEvidenceRequirement:
    evidence_type: str
    minimum_confidence: float
    required: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssessmentStrategyStep:
    sequence_number: int
    title: str
    goal: str
    recommended_item_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssessmentStrategy:
    strategy_type: str
    name: str
    objective: str
    recommended_item_types: list[str]
    evidence_requirements: list[AssessmentEvidenceRequirement]
    steps: list[AssessmentStrategyStep]
    estimated_difficulty: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssessmentBlueprint:
    content_concept_id: str
    content_concept_title: str
    strategy: AssessmentStrategy
    recommended_item_count: int
    allowed_item_types: list[str]
    mastery_signal: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssessmentDeliveryItem:
    sequence_number: int
    item: Any
    source_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


class AssessmentState(models.TextChoices):
    CREATED = "created", "Created"
    ACTIVE = "active", "Active"
    SUBMITTED = "submitted", "Submitted"
    EVALUATED = "evaluated", "Evaluated"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class AssessmentItemType(models.TextChoices):
    MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
    SHORT_ANSWER = "short_answer", "Short Answer"
    ESSAY = "essay", "Essay"
    CALCULATION = "calculation", "Calculation"
    MATCHING = "matching", "Matching"
    ORDERING = "ordering", "Ordering"
    TRUE_FALSE = "true_false", "True/False"
    DIAGRAM = "diagram", "Diagram"
    ORAL = "oral", "Oral"
    TEACH_BACK = "teach_back", "Teach Back"
    PROGRAMMING = "programming", "Programming"
    CLINICAL = "clinical", "Clinical"
    INTERVIEW = "interview", "Interview"
    OTHER = "other", "Other"


class AssessmentStrategyType(models.TextChoices):
    CONCEPT_CHECK = "concept_check", "Concept Check"
    KNOWLEDGE_RECALL = "knowledge_recall", "Knowledge Recall"
    WORKED_PROBLEM = "worked_problem", "Worked Problem"
    APPLIED_REASONING = "applied_reasoning", "Applied Reasoning"
    CALCULATION_PRACTICE = "calculation_practice", "Calculation Practice"
    REFLECTIVE_EXPLANATION = "reflective_explanation", "Reflective Explanation"
    TEACH_BACK_PREPARATION = "teach_back_preparation", "Teach-Back Preparation"
    ORAL_PROBE = "oral_probe", "Oral Probe"
    MIXED_EVIDENCE = "mixed_evidence", "Mixed Evidence"
    REVIEW_CHECK = "review_check", "Review Check"


class AssessmentDeliveryState(models.TextChoices):
    CREATED = "created", "Created"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    SUBMITTED = "submitted", "Submitted"
    COMPLETED = "completed", "Completed"
    ABANDONED = "abandoned", "Abandoned"


class EvaluatorType(models.TextChoices):
    DETERMINISTIC = "deterministic", "Deterministic"
    HUMAN = "human", "Human"
    AI = "ai", "AI"
    SYSTEM = "system", "System"


class ItemDifficulty(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    EASY = "easy", "Easy"
    MEDIUM = "medium", "Medium"
    HARD = "hard", "Hard"
    ADVANCED = "advanced", "Advanced"


class ItemReviewStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_REVIEW = "in_review", "In Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class ItemQualityStatus(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    LOW = "low", "Low"
    ACCEPTABLE = "acceptable", "Acceptable"
    HIGH = "high", "High"
    NEEDS_ATTENTION = "needs_attention", "Needs Attention"


class LearningEvidenceSourceType(models.TextChoices):
    ASSESSMENT_ATTEMPT = "assessment_attempt", "Assessment Attempt"
    ASSESSMENT_EVALUATION = "assessment_evaluation", "Assessment Evaluation"
    ASSESSMENT_RESULT = "assessment_result", "Assessment Result"
    TEACH_BACK = "teach_back", "Teach Back"
    ORAL_RESPONSE = "oral_response", "Oral Response"
    PROJECT = "project", "Project"
    SIMULATION = "simulation", "Simulation"
    MANUAL_REVIEW = "manual_review", "Manual Review"
    SYSTEM = "system", "System"


class LearningEvidenceType(models.TextChoices):
    CORRECT_RESPONSE = "correct_response", "Correct Response"
    PARTIAL_UNDERSTANDING = "partial_understanding", "Partial Understanding"
    MISCONCEPTION = "misconception", "Misconception"
    EXPLANATION_QUALITY = "explanation_quality", "Explanation Quality"
    APPLIED_REASONING = "applied_reasoning", "Applied Reasoning"
    COMPLETION = "completion", "Completion"
    MANUAL_OBSERVATION = "manual_observation", "Manual Observation"
    OTHER = "other", "Other"


class MasteryDecisionValue(models.TextChoices):
    NOT_ENOUGH_EVIDENCE = "not_enough_evidence", "Not Enough Evidence"
    NOT_MASTERED = "not_mastered", "Not Mastered"
    EMERGING = "emerging", "Emerging"
    MASTERED = "mastered", "Mastered"
    NEEDS_REVIEW = "needs_review", "Needs Review"


class Assessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_concept = models.ForeignKey(ContentConcept, on_delete=models.CASCADE, related_name="assessments")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    state = models.CharField(max_length=50, choices=AssessmentState.choices, default=AssessmentState.CREATED)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_concept"], name="assess_concept_idx"),
            models.Index(fields=["state"], name="assess_state_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title


class AssessmentItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=50, choices=AssessmentItemType.choices)
    prompt = models.TextField()
    sequence_number = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_item"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["assessment", "sequence_number"], name="unique_assessment_item_sequence"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="assessment_item_sequence_gte_1"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.assessment_id} #{self.sequence_number}"


class ItemBankEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_concept = models.ForeignKey(ContentConcept, on_delete=models.CASCADE, related_name="item_bank_entries")
    item_type = models.CharField(max_length=50, choices=AssessmentItemType.choices)
    prompt = models.TextField()
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=50, choices=ItemDifficulty.choices, default=ItemDifficulty.UNKNOWN)
    review_status = models.CharField(max_length=50, choices=ItemReviewStatus.choices, default=ItemReviewStatus.DRAFT)
    quality_status = models.CharField(max_length=50, choices=ItemQualityStatus.choices, default=ItemQualityStatus.UNKNOWN)
    authored_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="authored_item_bank_entries")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item_bank_entry"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_concept"], name="item_bank_concept_idx"),
            models.Index(fields=["item_type"], name="item_bank_type_idx"),
            models.Index(fields=["review_status"], name="item_bank_review_idx"),
            models.Index(fields=["quality_status"], name="item_bank_quality_idx"),
        ]


class ItemOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_bank_entry = models.ForeignKey(ItemBankEntry, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=100)
    content = models.TextField()
    is_correct = models.BooleanField(default=False)
    explanation = models.TextField(blank=True)
    sequence_number = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item_option"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["item_bank_entry", "sequence_number"], name="unique_item_option_sequence"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="item_option_sequence_gte_1"),
        ]


class AssessmentItemBankLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="item_bank_links")
    item_bank_entry = models.ForeignKey(ItemBankEntry, on_delete=models.CASCADE, related_name="assessment_links")
    sequence_number = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_item_bank_link"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["assessment", "sequence_number"], name="unique_assessment_bank_link_sequence"),
            models.UniqueConstraint(fields=["assessment", "item_bank_entry"], name="unique_assessment_bank_link_item"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="assessment_bank_link_sequence_gte_1"),
        ]


class AssessmentAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="attempts")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_attempts")
    state = models.CharField(max_length=50, choices=AssessmentState.choices, default=AssessmentState.ACTIVE)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_attempt"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assessment"], name="assess_attempt_assess_idx"),
            models.Index(fields=["learner"], name="assess_attempt_learner_idx"),
            models.Index(fields=["state"], name="assess_attempt_state_idx"),
        ]


class AssessmentDeliverySession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="delivery_sessions")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_delivery_sessions")
    assessment_attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.SET_NULL, null=True, blank=True, related_name="delivery_sessions")
    status = models.CharField(max_length=50, choices=AssessmentDeliveryState.choices, default=AssessmentDeliveryState.CREATED)
    current_sequence_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_delivery_session"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_sequence_number__gte=1),
                name="assessment_delivery_current_sequence_gte_1",
            ),
        ]
        indexes = [
            models.Index(fields=["assessment"], name="delivery_session_assess_idx"),
            models.Index(fields=["learner"], name="delivery_session_learner_idx"),
            models.Index(fields=["status"], name="delivery_session_status_idx"),
        ]


class AssessmentInteraction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=100)
    content = models.TextField(blank=True)
    sequence_number = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assessment_interaction"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "sequence_number"], name="unique_assessment_interaction_sequence"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="assessment_interaction_sequence_gte_1"),
        ]


class AssessmentResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name="responses")
    item = models.ForeignKey(AssessmentItem, on_delete=models.CASCADE, related_name="responses")
    response_data = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_response"
        ordering = ["submitted_at"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "item"], name="unique_attempt_item_response"),
        ]


class AssessmentEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.OneToOneField(AssessmentResponse, on_delete=models.CASCADE, related_name="evaluation")
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assessment_evaluations")
    score = models.FloatField(default=0.0)
    max_score = models.FloatField(default=1.0)
    is_correct = models.BooleanField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    evaluator_type = models.CharField(max_length=50, choices=EvaluatorType.choices, default=EvaluatorType.DETERMINISTIC)
    evaluation_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_evaluation"
        indexes = [
            models.Index(fields=["evaluator_type"], name="assessment_eval_type_idx"),
        ]


class AssessmentResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation = models.OneToOneField(AssessmentEvaluation, on_delete=models.CASCADE, null=True, blank=True, related_name="result")
    attempt = models.OneToOneField(AssessmentAttempt, on_delete=models.CASCADE, null=True, blank=True, related_name="result")
    total_score = models.FloatField(default=0.0)
    max_score = models.FloatField(default=0.0)
    percentage = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    result_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_result"
        indexes = [
            models.Index(fields=["attempt"], name="assessment_result_attempt_idx"),
        ]


class LearningEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_evidence")
    content_concept = models.ForeignKey(ContentConcept, on_delete=models.CASCADE, related_name="learning_evidence")
    source_type = models.CharField(max_length=50, choices=LearningEvidenceSourceType.choices)
    source_id = models.CharField(max_length=255)
    evidence_type = models.CharField(max_length=50, choices=LearningEvidenceType.choices)
    score = models.FloatField(null=True, blank=True)
    confidence = models.FloatField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "learning_evidence"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0.0) & models.Q(confidence__lte=1.0),
                name="learning_evidence_confidence_0_1",
            ),
            models.CheckConstraint(
                condition=models.Q(score__isnull=True) | (models.Q(score__gte=0.0) & models.Q(score__lte=1.0)),
                name="learning_evidence_score_null_or_0_1",
            ),
        ]
        indexes = [
            models.Index(fields=["learner"], name="learning_evidence_learner_idx"),
            models.Index(fields=["content_concept"], name="learning_evidence_concept_idx"),
            models.Index(fields=["source_type"], name="learning_evidence_source_idx"),
            models.Index(fields=["evidence_type"], name="learning_evidence_type_idx"),
        ]


class MasteryDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mastery_decisions")
    content_concept = models.ForeignKey(ContentConcept, on_delete=models.CASCADE, related_name="mastery_decisions")
    decision = models.CharField(max_length=50, choices=MasteryDecisionValue.choices)
    confidence = models.FloatField()
    evidence_count = models.PositiveIntegerField()
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mastery_decision"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0.0) & models.Q(confidence__lte=1.0),
                name="mastery_decision_confidence_0_1",
            ),
        ]
        indexes = [
            models.Index(fields=["learner"], name="mastery_decision_learner_idx"),
            models.Index(fields=["content_concept"], name="mastery_decision_concept_idx"),
            models.Index(fields=["decision"], name="mastery_decision_value_idx"),
        ]


class MasteryProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mastery_profiles")
    content_concept = models.ForeignKey(ContentConcept, on_delete=models.CASCADE, related_name="mastery_profiles")
    current_decision = models.CharField(max_length=50, choices=MasteryDecisionValue.choices)
    confidence = models.FloatField()
    evidence_count = models.PositiveIntegerField()
    last_evidence_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mastery_profile"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["learner", "content_concept"], name="unique_mastery_profile_learner_concept"),
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0.0) & models.Q(confidence__lte=1.0),
                name="mastery_profile_confidence_0_1",
            ),
        ]
        indexes = [
            models.Index(fields=["learner"], name="mastery_profile_learner_idx"),
            models.Index(fields=["content_concept"], name="mastery_profile_concept_idx"),
            models.Index(fields=["current_decision"], name="mastery_profile_decision_idx"),
        ]


__all__ = [
    "AssessmentEvidenceRequirement",
    "AssessmentStrategy",
    "AssessmentStrategyStep",
    "AssessmentBlueprint",
    "AssessmentDeliveryItem",
    "Assessment",
    "AssessmentItem",
    "ItemBankEntry",
    "ItemOption",
    "AssessmentItemBankLink",
    "AssessmentAttempt",
    "AssessmentDeliverySession",
    "AssessmentInteraction",
    "AssessmentResponse",
    "AssessmentEvaluation",
    "AssessmentResult",
    "LearningEvidence",
    "MasteryDecision",
    "MasteryProfile",
    "AssessmentState",
    "AssessmentItemType",
    "AssessmentStrategyType",
    "AssessmentDeliveryState",
    "EvaluatorType",
    "ItemDifficulty",
    "ItemReviewStatus",
    "ItemQualityStatus",
    "LearningEvidenceSourceType",
    "LearningEvidenceType",
    "MasteryDecisionValue",
]
