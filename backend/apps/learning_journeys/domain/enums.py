from __future__ import annotations

from django.db import models


class LearningJourneyType(models.TextChoices):
    SELF_STUDY = "SELF_STUDY", "Self-study"
    INSTITUTIONAL = "INSTITUTIONAL", "Institutional"


class LearningJourneyStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    DISCOVERING_GOAL = "DISCOVERING_GOAL", "Discovering goal"
    INTENT_CONFIRMED = "INTENT_CONFIRMED", "Intent confirmed"
    RESOLVING_CURRICULUM = "RESOLVING_CURRICULUM", "Resolving curriculum"
    CURRICULUM_UNRESOLVED = "CURRICULUM_UNRESOLVED", "Curriculum unresolved"
    CURRICULUM_MATCHED = "CURRICULUM_MATCHED", "Curriculum matched"
    SUBJECT_BINDING_REQUIRED = "SUBJECT_BINDING_REQUIRED", "Subject binding required"
    SUBJECT_BINDING_UNAVAILABLE = "SUBJECT_BINDING_UNAVAILABLE", "Subject binding unavailable"
    SUBJECT_BOUND = "SUBJECT_BOUND", "Subject bound"
    STARTING_STATE_REQUIRED = "STARTING_STATE_REQUIRED", "Starting state required"
    STARTING_STATE_IN_PROGRESS = "STARTING_STATE_IN_PROGRESS", "Starting state in progress"
    STARTING_STATE_CONFIRMED = "STARTING_STATE_CONFIRMED", "Starting state confirmed"
    BRIDGE_REQUIRED = "BRIDGE_REQUIRED", "Bridge required"
    PLAN_REQUIRED = "PLAN_REQUIRED", "Plan required"
    PLAN_READY = "PLAN_READY", "Plan ready"
    LEARNING_ACTIVE = "LEARNING_ACTIVE", "Learning active"
    LEARNING_BLOCKED = "LEARNING_BLOCKED", "Learning blocked"
    PAUSED = "PAUSED", "Paused"
    LEARNING_GOAL_COMPLETED = "LEARNING_GOAL_COMPLETED", "Learning goal completed"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    ARCHIVED = "ARCHIVED", "Archived"


class LearningJourneyStatusReasonCode(models.TextChoices):
    JOURNEY_CREATED = "JOURNEY_CREATED", "Journey created"
    INTENT_NOT_CONFIRMED = "INTENT_NOT_CONFIRMED", "Intent not confirmed"
    CURRICULUM_RESOLUTION_PENDING = "CURRICULUM_RESOLUTION_PENDING", "Curriculum resolution pending"
    NO_GOVERNED_CURRICULUM = "NO_GOVERNED_CURRICULUM", "No governed curriculum"
    CURRICULUM_SELECTION_REQUIRED = "CURRICULUM_SELECTION_REQUIRED", "Curriculum selection required"
    SELF_STUDY_BINDING_MISSING = "SELF_STUDY_BINDING_MISSING", "Self-study binding missing"
    DIAGNOSTIC_REQUIRED = "DIAGNOSTIC_REQUIRED", "Diagnostic required"
    DIAGNOSTIC_IN_PROGRESS = "DIAGNOSTIC_IN_PROGRESS", "Diagnostic in progress"
    PLACEMENT_PENDING = "PLACEMENT_PENDING", "Placement pending"
    BRIDGE_PLAN_REQUIRED = "BRIDGE_PLAN_REQUIRED", "Bridge plan required"
    LEARNING_PLAN_REQUIRED = "LEARNING_PLAN_REQUIRED", "Learning plan required"
    TEACHING_NOT_READY = "TEACHING_NOT_READY", "Teaching not ready"
    ACTIVE_REMEDIATION = "ACTIVE_REMEDIATION", "Active remediation"
    MANUALLY_PAUSED = "MANUALLY_PAUSED", "Manually paused"
    GOAL_COMPLETED = "GOAL_COMPLETED", "Goal completed"
    WITHDRAWN_BY_LEARNER = "WITHDRAWN_BY_LEARNER", "Withdrawn by learner"
    ARCHIVED_BY_POLICY = "ARCHIVED_BY_POLICY", "Archived by policy"
    INSTITUTIONAL_ASSIGNMENT_REQUIRED = "INSTITUTIONAL_ASSIGNMENT_REQUIRED", "Institutional assignment required"


class LearningJourneySourceType(models.TextChoices):
    SELF_STUDY_WORKSPACE = "SELF_STUDY_WORKSPACE", "Self-study workspace"
    INSTITUTION_MEMBERSHIP = "INSTITUTION_MEMBERSHIP", "Institution membership"
    INSTITUTIONAL_ASSIGNMENT = "INSTITUTIONAL_ASSIGNMENT", "Institutional assignment"


class LearningJourneySubjectBindingSource(models.TextChoices):
    SELF_STUDY_CURRICULUM_RESOLUTION = "SELF_STUDY_CURRICULUM_RESOLUTION", "Self-study curriculum resolution"
    INSTITUTIONAL_ASSIGNMENT = "INSTITUTIONAL_ASSIGNMENT", "Institutional assignment"
    ADMINISTRATIVE_REPAIR = "ADMINISTRATIVE_REPAIR", "Administrative repair"


class LearningJourneySubjectBindingStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    INVALIDATED = "INVALIDATED", "Invalidated"


class LearningJourneyStepCode(models.TextChoices):
    DISCOVER_GOAL = "DISCOVER_GOAL", "Discover goal"
    CONFIRM_INTENT = "CONFIRM_INTENT", "Confirm intent"
    RESOLVE_CURRICULUM = "RESOLVE_CURRICULUM", "Resolve curriculum"
    SELECT_CURRICULUM = "SELECT_CURRICULUM", "Select curriculum"
    WAIT_FOR_SUBJECT_BINDING = "WAIT_FOR_SUBJECT_BINDING", "Wait for subject binding"
    COMPLETE_ENTRY_DIAGNOSTIC = "COMPLETE_ENTRY_DIAGNOSTIC", "Complete entry diagnostic"
    REVIEW_PLACEMENT = "REVIEW_PLACEMENT", "Review placement"
    COMPLETE_BRIDGE = "COMPLETE_BRIDGE", "Complete bridge"
    CREATE_LEARNING_PLAN = "CREATE_LEARNING_PLAN", "Create learning plan"
    BEGIN_LEARNING = "BEGIN_LEARNING", "Begin learning"
    CONTINUE_LEARNING = "CONTINUE_LEARNING", "Continue learning"
    RESOLVE_BLOCKER = "RESOLVE_BLOCKER", "Resolve blocker"
    REVIEW_PROGRESS = "REVIEW_PROGRESS", "Review progress"
    GOAL_COMPLETED = "GOAL_COMPLETED", "Goal completed"


class LearningJourneyActionCode(models.TextChoices):
    BEGIN_GOAL_DISCOVERY = "BEGIN_GOAL_DISCOVERY", "Begin goal discovery"
    CONTINUE_GOAL_DISCOVERY = "CONTINUE_GOAL_DISCOVERY", "Continue goal discovery"
    CONFIRM_INTENT = "CONFIRM_INTENT", "Confirm intent"
    REVISE_INTENT = "REVISE_INTENT", "Revise intent"
    RESOLVE_CURRICULUM = "RESOLVE_CURRICULUM", "Resolve curriculum"
    RETRY_CURRICULUM_RESOLUTION = "RETRY_CURRICULUM_RESOLUTION", "Retry curriculum resolution"
    SELECT_CURRICULUM = "SELECT_CURRICULUM", "Select curriculum"
    BEGIN_DIAGNOSTIC = "BEGIN_DIAGNOSTIC", "Begin diagnostic"
    CONTINUE_DIAGNOSTIC = "CONTINUE_DIAGNOSTIC", "Continue diagnostic"
    CONFIRM_PLACEMENT = "CONFIRM_PLACEMENT", "Confirm placement"
    GENERATE_BRIDGE_PLAN = "GENERATE_BRIDGE_PLAN", "Generate bridge plan"
    GENERATE_LEARNING_PLAN = "GENERATE_LEARNING_PLAN", "Generate learning plan"
    ACTIVATE_LEARNING_PLAN = "ACTIVATE_LEARNING_PLAN", "Activate learning plan"
    PREPARE_TEACHING_SESSION = "PREPARE_TEACHING_SESSION", "Prepare teaching session"
    BEGIN_TEACHING_SESSION = "BEGIN_TEACHING_SESSION", "Begin teaching session"
    CONTINUE_TEACHING_SESSION = "CONTINUE_TEACHING_SESSION", "Continue teaching session"
    RETRY_BLOCKED_STEP = "RETRY_BLOCKED_STEP", "Retry blocked step"
    PAUSE_JOURNEY = "PAUSE_JOURNEY", "Pause journey"
    RESUME_JOURNEY = "RESUME_JOURNEY", "Resume journey"
    WITHDRAW_JOURNEY = "WITHDRAW_JOURNEY", "Withdraw journey"
    SYNCHRONIZE = "SYNCHRONIZE", "Synchronize"


class LearningJourneyBlockerCode(models.TextChoices):
    NO_CONFIRMED_INTENT = "NO_CONFIRMED_INTENT", "No confirmed intent"
    NO_GOVERNED_CURRICULUM = "NO_GOVERNED_CURRICULUM", "No governed curriculum"
    CURRICULUM_SELECTION_REQUIRED = "CURRICULUM_SELECTION_REQUIRED", "Curriculum selection required"
    SELF_STUDY_SUBJECT_BINDING_UNAVAILABLE = "SELF_STUDY_SUBJECT_BINDING_UNAVAILABLE", "Self-study subject binding unavailable"
    DIAGNOSTIC_NOT_READY = "DIAGNOSTIC_NOT_READY", "Diagnostic not ready"
    PLACEMENT_NOT_CONFIRMED = "PLACEMENT_NOT_CONFIRMED", "Placement not confirmed"
    BRIDGE_PLAN_NOT_READY = "BRIDGE_PLAN_NOT_READY", "Bridge plan not ready"
    LEARNING_PLAN_NOT_READY = "LEARNING_PLAN_NOT_READY", "Learning plan not ready"
    TEACHING_CONTENT_NOT_READY = "TEACHING_CONTENT_NOT_READY", "Teaching content not ready"
    ACTIVE_REMEDIATION_REQUIRED = "ACTIVE_REMEDIATION_REQUIRED", "Active remediation required"
    INSTITUTIONAL_AUTHORITY_MISSING = "INSTITUTIONAL_AUTHORITY_MISSING", "Institutional authority missing"
    INSTITUTIONAL_ASSIGNMENT_REQUIRED = "INSTITUTIONAL_ASSIGNMENT_REQUIRED", "Institutional assignment required"
    SOURCE_RECORD_MISSING = "SOURCE_RECORD_MISSING", "Source record missing"
    UNEXPECTED_SOURCE_STATE = "UNEXPECTED_SOURCE_STATE", "Unexpected source state"


class LearningJourneyActionReceiptStatus(models.TextChoices):
    ACCEPTED = "ACCEPTED", "Accepted"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    REJECTED = "REJECTED", "Rejected"
    NO_OP = "NO_OP", "No-op"
    CONFLICT = "CONFLICT", "Conflict"


class LearningJourneyOperationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class LearningJourneyCommandResult(models.TextChoices):
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    NO_OP = "NO_OP", "No-op"
    FAILED = "FAILED", "Failed"
    CONFLICT = "CONFLICT", "Conflict"


class LearningJourneyIntegritySeverity(models.TextChoices):
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    BLOCKING = "BLOCKING", "Blocking"
    CRITICAL = "CRITICAL", "Critical"


class LearningJourneyIntegrityFindingStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    RESOLVED = "RESOLVED", "Resolved"
    DISMISSED = "DISMISSED", "Dismissed"


class LearningJourneyIntegrityFindingCode(models.TextChoices):
    MISSING_SOURCE_BINDING = "MISSING_SOURCE_BINDING", "Missing source binding"
    DUPLICATE_ACTIVE_SUBJECT_BINDING = "DUPLICATE_ACTIVE_SUBJECT_BINDING", "Duplicate active subject binding"
    JOURNEY_SOURCE_LEARNER_MISMATCH = "JOURNEY_SOURCE_LEARNER_MISMATCH", "Journey source learner mismatch"
    JOURNEY_INSTITUTION_MISMATCH = "JOURNEY_INSTITUTION_MISMATCH", "Journey institution mismatch"
    INVALID_ACTIVE_SESSION_REFERENCE = "INVALID_ACTIVE_SESSION_REFERENCE", "Invalid active session reference"
    INVALID_PLAN_REFERENCE = "INVALID_PLAN_REFERENCE", "Invalid plan reference"
    STALE_AUTHORITY_PROJECTION = "STALE_AUTHORITY_PROJECTION", "Stale authority projection"
    PROJECTION_VERSION_MISMATCH = "PROJECTION_VERSION_MISMATCH", "Projection version mismatch"
    TERMINAL_JOURNEY_WITH_ACTIVE_OPERATION = "TERMINAL_JOURNEY_WITH_ACTIVE_OPERATION", "Terminal journey with active operation"
    INSTITUTIONAL_JOURNEY_WITHOUT_ACTIVE_AUTHORITY = "INSTITUTIONAL_JOURNEY_WITHOUT_ACTIVE_AUTHORITY", "Institutional journey without active authority"
    SELF_STUDY_JOURNEY_WITH_INSTITUTIONAL_AUTHORITY = "SELF_STUDY_JOURNEY_WITH_INSTITUTIONAL_AUTHORITY", "Self-study journey with institutional authority"


class LearningCompetencyProgressState(models.TextChoices):
    NOT_STARTED = "NOT_STARTED", "Not started"
    EMERGING = "EMERGING", "Emerging"
    DEVELOPING = "DEVELOPING", "Developing"
    DEMONSTRATED = "DEMONSTRATED", "Demonstrated"
    REINFORCED = "REINFORCED", "Reinforced"
    REVIEW_REQUIRED = "REVIEW_REQUIRED", "Review required"
    REGRESSED = "REGRESSED", "Regressed"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class LearningCompetencyUnlockState(models.TextChoices):
    LOCKED = "LOCKED", "Locked"
    AVAILABLE = "AVAILABLE", "Available"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class LearningCompetencyProgressReason(models.TextChoices):
    INITIALIZED = "INITIALIZED", "Initialized"
    MASTERY_EMERGING = "MASTERY_EMERGING", "Mastery emerging"
    MASTERY_DEMONSTRATED = "MASTERY_DEMONSTRATED", "Mastery demonstrated"
    MASTERY_REINFORCED = "MASTERY_REINFORCED", "Mastery reinforced"
    REVIEW_REQUIRED = "REVIEW_REQUIRED", "Review required"
    REGRESSION_EVIDENCE = "REGRESSION_EVIDENCE", "Regression evidence"
    CURRICULUM_SUPERSEDED = "CURRICULUM_SUPERSEDED", "Curriculum superseded"
    UNCHANGED = "UNCHANGED", "Unchanged"


class JourneyAuthorityProviderType(models.TextChoices):
    SELF_STUDY = "SELF_STUDY", "Self-study"
    INSTITUTION = "INSTITUTION", "Institution"


class InstitutionalAssignmentState(models.TextChoices):
    ASSIGNED = "ASSIGNED", "Assigned"
    ACCEPTED = "ACCEPTED", "Accepted"
    ACTIVE = "ACTIVE", "Active"
    ON_HOLD = "ON_HOLD", "On hold"
    INTERVENTION_REQUIRED = "INTERVENTION_REQUIRED", "Intervention required"
    COMPLETION_PENDING = "COMPLETION_PENDING", "Completion pending"
    COMPLETED = "COMPLETED", "Completed"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class InstitutionalAcceptanceMode(models.TextChoices):
    AUTO_ACCEPT = "AUTO_ACCEPT", "Auto accept"
    LEARNER_CONFIRMATION_REQUIRED = "LEARNER_CONFIRMATION_REQUIRED", "Learner confirmation required"
    ADMIN_CONFIRMATION_REQUIRED = "ADMIN_CONFIRMATION_REQUIRED", "Admin confirmation required"


class InstitutionalCompletionState(models.TextChoices):
    PENDING = "PENDING", "Pending"
    READY = "READY", "Ready"
    COMPLETED = "COMPLETED", "Completed"
    BLOCKED = "BLOCKED", "Blocked"


class InstitutionalInterventionReason(models.TextChoices):
    REPEATED_REVIEW_REQUIRED = "REPEATED_REVIEW_REQUIRED", "Repeated review required"
    PERSISTENT_REGRESSION = "PERSISTENT_REGRESSION", "Persistent regression"
    REQUIRED_COMPETENCY_OVERDUE = "REQUIRED_COMPETENCY_OVERDUE", "Required competency overdue"
    LEARNING_INACTIVITY = "LEARNING_INACTIVITY", "Learning inactivity"


class InstitutionalInterventionSeverity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class InstitutionalInterventionStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    RESOLVED = "RESOLVED", "Resolved"
    DISMISSED = "DISMISSED", "Dismissed"
