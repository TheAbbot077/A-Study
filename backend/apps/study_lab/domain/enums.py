"""
Study Lab domain enums.

All enums follow the project convention of using Django TextChoices.
"""

from django.db import models


class WorkspaceType(models.TextChoices):
    SELF_STUDY = "SELF_STUDY", "Self-study"
    INSTITUTIONAL = "INSTITUTIONAL", "Institutional"
    HYBRID = "HYBRID", "Hybrid"
    PERSONAL_REVIEW = "PERSONAL_REVIEW", "Personal review"


class WorkspaceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    SUSPENDED = "SUSPENDED", "Suspended"
    COMPLETED = "COMPLETED", "Completed"
    ARCHIVED = "ARCHIVED", "Archived"


class PanelKey(models.TextChoices):
    MENTOR = "MENTOR", "Mentor"
    WHITEBOARD = "WHITEBOARD", "Whiteboard"
    RESOURCES = "RESOURCES", "Resources"
    ARIEL = "ARIEL", "Ariel"
    CONCEPT_CHECK = "CONCEPT_CHECK", "Concept Check"
    PROGRESS = "PROGRESS", "Progress"
    NOTES = "NOTES", "Notes"
    JOURNEY = "JOURNEY", "Journey"
    ACTIVITY = "ACTIVITY", "Activity"


class ToolKey(models.TextChoices):
    ABBOT_MENTOR = "ABBOT_MENTOR", "Abbot Mentor"
    ARIEL_TEACH = "ARIEL_TEACH", "Ariel Teach"
    STRUCTURED_WHITEBOARD = "STRUCTURED_WHITEBOARD", "Structured Whiteboard"
    RESOURCE_VIEWER = "RESOURCE_VIEWER", "Resource Viewer"
    CONCEPT_CHECK = "CONCEPT_CHECK", "Concept Check"
    LEARNER_NOTES = "LEARNER_NOTES", "Learner Notes"
    PROGRESS_VIEW = "PROGRESS_VIEW", "Progress View"
    JOURNEY_MAP = "JOURNEY_MAP", "Journey Map"
    RESUME_SESSION = "RESUME_SESSION", "Resume Session"
    STANDARD_CALCULATOR = "STANDARD_CALCULATOR", "Standard Calculator"
    SCIENTIFIC_CALCULATOR = "SCIENTIFIC_CALCULATOR", "Scientific Calculator"
    GRAPHING_CALCULATOR = "GRAPHING_CALCULATOR", "Graphing Calculator"
    UNIT_CONVERTER = "UNIT_CONVERTER", "Unit Converter"
    EQUATION_WORKSPACE = "EQUATION_WORKSPACE", "Equation Workspace"
    FORMULA_SHEET = "FORMULA_SHEET", "Formula Sheet"
    MATH_SCRATCHPAD = "MATH_SCRATCHPAD", "Math Scratchpad"
    TABLE_BUILDER = "TABLE_BUILDER", "Table Builder"
    DIAGRAM_STUDIO = "DIAGRAM_STUDIO", "Diagram Studio"
    CONCEPT_MAP = "CONCEPT_MAP", "Concept Map"
    FLOWCHART = "FLOWCHART", "Flowchart"
    TIMELINE = "TIMELINE", "Timeline"
    COMPARISON_TABLE = "COMPARISON_TABLE", "Comparison Table"
    FLASHCARD_WORKSPACE = "FLASHCARD_WORKSPACE", "Flashcard Workspace"
    STRUCTURED_SCRATCHPAD = "STRUCTURED_SCRATCHPAD", "Structured Scratchpad"
    NOTE_CARDS = "NOTE_CARDS", "Note Cards"
    CHECKLIST = "CHECKLIST", "Checklist"
    CODE_EDITOR = "CODE_EDITOR", "Code Editor"


class ToolStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    RETIRED = "RETIRED", "Retired"


class ToolCategory(models.TextChoices):
    TEACHING = "TEACHING", "Teaching"
    LEARNING = "LEARNING", "Learning"
    REVIEW = "REVIEW", "Review"
    ORGANIZATION = "ORGANIZATION", "Organization"
    ASSESSMENT = "ASSESSMENT", "Assessment"


class ProviderContext(models.TextChoices):
    ABBOT = "ABBOT", "Abbot"
    ARIEL = "ARIEL", "Ariel"
    WHITEBOARD = "WHITEBOARD", "Whiteboard"
    RESOURCE = "RESOURCE", "Resource"
    CONCEPT_CHECK = "CONCEPT_CHECK", "Concept Check"
    PROGRESS = "PROGRESS", "Progress"
    JOURNEY = "JOURNEY", "Journey"
    STUDY_LAB = "STUDY_LAB", "Study Lab"


class ToolAvailabilityReasonCode(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    WORKSPACE_NOT_ACTIVE = "WORKSPACE_NOT_ACTIVE", "Workspace not active"
    WORKSPACE_SUSPENDED = "WORKSPACE_SUSPENDED", "Workspace suspended"
    WORKSPACE_ARCHIVED = "WORKSPACE_ARCHIVED", "Workspace archived"
    CAPABILITY_REQUIRED = "CAPABILITY_REQUIRED", "Capability required"
    INSTITUTION_POLICY_RESTRICTED = "INSTITUTION_POLICY_RESTRICTED", "Institution policy restricted"
    LEARNER_NOT_ELIGIBLE = "LEARNER_NOT_ELIGIBLE", "Learner not eligible"
    ARIEL_NOT_ACTIVATED = "ARIEL_NOT_ACTIVATED", "Ariel not activated"
    NO_ACTIVE_SUBJECT = "NO_ACTIVE_SUBJECT", "No active subject"
    NO_ACTIVE_JOURNEY = "NO_ACTIVE_JOURNEY", "No active journey"
    TEACHING_NOT_READY = "TEACHING_NOT_READY", "Teaching not ready"
    RESOURCE_NOT_READY = "RESOURCE_NOT_READY", "Resource not ready"
    RETRIEVAL_NOT_READY = "RETRIEVAL_NOT_READY", "Retrieval not ready"
    CONCEPT_CHECK_NOT_AVAILABLE = "CONCEPT_CHECK_NOT_AVAILABLE", "Concept check not available"
    WHITEBOARD_NOT_AVAILABLE = "WHITEBOARD_NOT_AVAILABLE", "Whiteboard not available"
    CONSENT_REQUIRED = "CONSENT_REQUIRED", "Consent required"
    AGE_POLICY_RESTRICTED = "AGE_POLICY_RESTRICTED", "Age policy restricted"
    TENANT_MISMATCH = "TENANT_MISMATCH", "Tenant mismatch"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE", "Provider unavailable"


class InvocationStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    ACCEPTED = "ACCEPTED", "Accepted"
    COMPLETED = "COMPLETED", "Completed"
    REJECTED = "REJECTED", "Rejected"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class NoteStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"
    DELETED = "DELETED", "Deleted"


class ActivityType(models.TextChoices):
    WORKSPACE_CREATED = "WORKSPACE_CREATED", "Workspace created"
    WORKSPACE_OPENED = "WORKSPACE_OPENED", "Workspace opened"
    WORKSPACE_ACTIVATED = "WORKSPACE_ACTIVATED", "Workspace activated"
    WORKSPACE_PAUSED = "WORKSPACE_PAUSED", "Workspace paused"
    WORKSPACE_RESUMED = "WORKSPACE_RESUMED", "Workspace resumed"
    WORKSPACE_COMPLETED = "WORKSPACE_COMPLETED", "Workspace completed"
    WORKSPACE_ARCHIVED = "WORKSPACE_ARCHIVED", "Workspace archived"
    SUBJECT_SELECTED = "SUBJECT_SELECTED", "Subject selected"
    CONCEPT_SELECTED = "CONCEPT_SELECTED", "Concept selected"
    PANEL_OPENED = "PANEL_OPENED", "Panel opened"
    TOOL_INVOKED = "TOOL_INVOKED", "Tool invoked"
    RESOURCE_OPENED = "RESOURCE_OPENED", "Resource opened"
    ABBOT_SESSION_RESUMED = "ABBOT_SESSION_RESUMED", "Abbot session resumed"
    ARIEL_SESSION_STARTED = "ARIEL_SESSION_STARTED", "Ariel session started"
    WHITEBOARD_RESUMED = "WHITEBOARD_RESUMED", "Whiteboard resumed"
    CONCEPT_CHECK_STARTED = "CONCEPT_CHECK_STARTED", "Concept check started"
    NOTE_CREATED = "NOTE_CREATED", "Note created"
    NOTE_UPDATED = "NOTE_UPDATED", "Note updated"
    CONTEXT_CHANGED = "CONTEXT_CHANGED", "Context changed"
    RESUME_POINT_UPDATED = "RESUME_POINT_UPDATED", "Resume point updated"


class ResumeOutcome(models.TextChoices):
    RESUME_ABBOT_SESSION = "RESUME_ABBOT_SESSION", "Resume Abbot session"
    RESUME_ARIEL_SESSION = "RESUME_ARIEL_SESSION", "Resume Ariel session"
    RESUME_WHITEBOARD = "RESUME_WHITEBOARD", "Resume whiteboard"
    RESUME_CONCEPT_CHECK = "RESUME_CONCEPT_CHECK", "Resume concept check"
    RETURN_TO_SUBJECT = "RETURN_TO_SUBJECT", "Return to subject"
    RETURN_TO_JOURNEY = "RETURN_TO_JOURNEY", "Return to journey"
    OPEN_RECOMMENDED_RESOURCE = "OPEN_RECOMMENDED_RESOURCE", "Open recommended resource"
    START_NEXT_CONCEPT = "START_NEXT_CONCEPT", "Start next concept"
    NO_ACTIVE_RESUME_POINT = "NO_ACTIVE_RESUME_POINT", "No active resume point"


class NextActionKey(models.TextChoices):
    CONTINUE_TEACHING = "CONTINUE_TEACHING", "Continue teaching"
    REVIEW_CONCEPT = "REVIEW_CONCEPT", "Review concept"
    TEACH_ARIEL = "TEACH_ARIEL", "Teach Ariel"
    COMPLETE_CONCEPT_CHECK = "COMPLETE_CONCEPT_CHECK", "Complete concept check"
    OPEN_RESOURCE = "OPEN_RESOURCE", "Open resource"
    RESUME_WHITEBOARD = "RESUME_WHITEBOARD", "Resume whiteboard"
    RETURN_TO_JOURNEY = "RETURN_TO_JOURNEY", "Return to journey"
    START_NEXT_CONCEPT = "START_NEXT_CONCEPT", "Start next concept"
    WAIT_FOR_CONTENT_READINESS = "WAIT_FOR_CONTENT_READINESS", "Wait for content readiness"
    NO_RECOMMENDATION = "NO_RECOMMENDATION", "No recommendation"


class SnapshotStatus(models.TextChoices):
    CURRENT = "CURRENT", "Current"
    STALE = "STALE", "Stale"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    FAILED = "FAILED", "Failed"


class WorkspaceFailureCode(models.TextChoices):
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND", "Workspace not found"
    WORKSPACE_ACCESS_DENIED = "WORKSPACE_ACCESS_DENIED", "Workspace access denied"
    WORKSPACE_TENANT_MISMATCH = "WORKSPACE_TENANT_MISMATCH", "Workspace tenant mismatch"
    WORKSPACE_INVALID_TRANSITION = "WORKSPACE_INVALID_TRANSITION", "Workspace invalid transition"
    WORKSPACE_NOT_ACTIVE = "WORKSPACE_NOT_ACTIVE", "Workspace not active"
    WORKSPACE_SUSPENDED = "WORKSPACE_SUSPENDED", "Workspace suspended"
    WORKSPACE_ARCHIVED = "WORKSPACE_ARCHIVED", "Workspace archived"
    CONTEXT_NOT_ACCESSIBLE = "CONTEXT_NOT_ACCESSIBLE", "Context not accessible"
    CONTEXT_MISMATCH = "CONTEXT_MISMATCH", "Context mismatch"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND", "Tool not found"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE", "Tool unavailable"
    TOOL_CAPABILITY_REQUIRED = "TOOL_CAPABILITY_REQUIRED", "Tool capability required"
    TOOL_PROVIDER_UNAVAILABLE = "TOOL_PROVIDER_UNAVAILABLE", "Tool provider unavailable"
    TOOL_INVOCATION_FAILED = "TOOL_INVOCATION_FAILED", "Tool invocation failed"
    NOTE_NOT_FOUND = "NOTE_NOT_FOUND", "Note not found"
    NOTE_ACCESS_DENIED = "NOTE_ACCESS_DENIED", "Note access denied"
    SNAPSHOT_NOT_AVAILABLE = "SNAPSHOT_NOT_AVAILABLE", "Snapshot not available"
    ASSEMBLY_PROVIDER_FAILURE = "ASSEMBLY_PROVIDER_FAILURE", "Assembly provider failure"


class StudyArtefactType(models.TextChoices):
    TEXT_NOTE = "TEXT_NOTE", "Text note"
    FLASHCARD_SET = "FLASHCARD_SET", "Flashcard set"
    FLASHCARD = "FLASHCARD", "Flashcard"
    FORMULA_SHEET = "FORMULA_SHEET", "Formula sheet"
    EQUATION_ARTEFACT = "EQUATION_ARTEFACT", "Equation artefact"
    GRAPH_ARTEFACT = "GRAPH_ARTEFACT", "Graph artefact"
    REVISION_SUMMARY = "REVISION_SUMMARY", "Revision summary"
    WHITEBOARD_SNAPSHOT = "WHITEBOARD_SNAPSHOT", "Whiteboard snapshot"
    RESOURCE_EXCERPT = "RESOURCE_EXCERPT", "Resource excerpt"
    SESSION_SUMMARY = "SESSION_SUMMARY", "Session summary"
    LESSON_REFERENCE = "LESSON_REFERENCE", "Lesson reference"
    CONCEPT_REFERENCE = "CONCEPT_REFERENCE", "Concept reference"
    CONCEPT_MAP = "CONCEPT_MAP", "Concept map"
    FLOWCHART = "FLOWCHART", "Flowchart"
    TIMELINE = "TIMELINE", "Timeline"
    COMPARISON_TABLE = "COMPARISON_TABLE", "Comparison table"
    DIAGRAM_ARTEFACT = "DIAGRAM_ARTEFACT", "Diagram artefact"
    LEARNER_EXPLANATION = "LEARNER_EXPLANATION", "Learner explanation"
    ARIEL_TEACHING_ARTEFACT = "ARIEL_TEACHING_ARTEFACT", "Ariel teaching artefact"
    ABBOT_LESSON_REFERENCE = "ABBOT_LESSON_REFERENCE", "Abbot lesson reference"
    CONCEPT_CHECK_RECEIPT = "CONCEPT_CHECK_RECEIPT", "Concept check receipt"
    SCRATCHPAD_ARTEFACT = "SCRATCHPAD_ARTEFACT", "Scratchpad artefact"
    NOTE_CARD_SET = "NOTE_CARD_SET", "Note card set"
    DATA_TABLE = "DATA_TABLE", "Data table"
    CODE_ARTEFACT = "CODE_ARTEFACT", "Code artefact"


class StudyArtefactVisibility(models.TextChoices):
    PRIVATE = "PRIVATE", "Private"
    WORKSPACE = "WORKSPACE", "Workspace"
    INSTITUTION_SHARED = "INSTITUTION_SHARED", "Institution shared"
    EXPLICIT_RECIPIENTS = "EXPLICIT_RECIPIENTS", "Explicit recipients"


class StudyArtefactLifecycle(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class StudyArtefactOrigin(models.TextChoices):
    NATIVE = "NATIVE", "Native"
    REFERENCED = "REFERENCED", "Referenced"
    IMPORTED = "IMPORTED", "Imported"
    EXPORTED = "EXPORTED", "Exported"
    TRANSFORMED = "TRANSFORMED", "Transformed"
    GENERATED = "GENERATED", "Generated"


class StudyArtefactCompatibilityStatus(models.TextChoices):
    COMPATIBLE = "COMPATIBLE", "Compatible"
    TRANSFORMATION_REQUIRED = "TRANSFORMATION_REQUIRED", "Transformation required"
    UNSUPPORTED_TYPE = "UNSUPPORTED_TYPE", "Unsupported type"
    UNSUPPORTED_SCHEMA = "UNSUPPORTED_SCHEMA", "Unsupported schema"
    ACCESS_DENIED = "ACCESS_DENIED", "Access denied"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE", "Provider unavailable"
    ARTEFACT_ARCHIVED = "ARTEFACT_ARCHIVED", "Artefact archived"
    SHARING_NOT_ALLOWED = "SHARING_NOT_ALLOWED", "Sharing not allowed"


class StudyArtefactLineageRelation(models.TextChoices):
    DERIVED_FROM = "DERIVED_FROM", "Derived from"
    TRANSFORMED_FROM = "TRANSFORMED_FROM", "Transformed from"
    SUMMARISES = "SUMMARISES", "Summarises"
    ANNOTATES = "ANNOTATES", "Annotates"
    EXTRACTED_FROM = "EXTRACTED_FROM", "Extracted from"
    COMBINED_FROM = "COMBINED_FROM", "Combined from"
    SUPERSEDES = "SUPERSEDES", "Supersedes"
    SHARED_WITH = "SHARED_WITH", "Shared with"
    EXPORTED_TO = "EXPORTED_TO", "Exported to"


class StudyToolManifestStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    RETIRED = "RETIRED", "Retired"


class InstrumentFamily(models.TextChoices):
    COMPUTATIONAL = "COMPUTATIONAL", "Computational"
    GRAPHING = "GRAPHING", "Graphing"
    MATHEMATICAL_CONSTRUCTION = "MATHEMATICAL_CONSTRUCTION", "Mathematical construction"
    VISUAL_REASONING = "VISUAL_REASONING", "Visual reasoning"
    MEMORY_AND_REVIEW = "MEMORY_AND_REVIEW", "Memory and review"
    GENERAL_THINKING = "GENERAL_THINKING", "General thinking"
    TECHNICAL = "TECHNICAL", "Technical"


class InstrumentAuthorship(models.TextChoices):
    LEARNER_AUTHORED = "LEARNER_AUTHORED", "Learner authored"
    LEARNER_EDITED = "LEARNER_EDITED", "Learner edited"
    TOOL_GENERATED = "TOOL_GENERATED", "Tool generated"
    AI_GENERATED = "AI_GENERATED", "AI generated"
    SOURCE_REFERENCED = "SOURCE_REFERENCED", "Source referenced"
    MIXED = "MIXED", "Mixed"


class CodeExecutionStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"


class WorkspaceToolSessionStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    SUSPENDED = "SUSPENDED", "Suspended"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    ABANDONED = "ABANDONED", "Abandoned"


class ArtefactTransformationRequestStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    VALIDATING = "VALIDATING", "Validating"
    READY = "READY", "Ready"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class ToolInvocationLifecycleStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    VALIDATED = "VALIDATED", "Validated"
    DISPATCHED = "DISPATCHED", "Dispatched"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class StudyScaffoldGenerationType(models.TextChoices):
    EQUATION_AND_FORMULA_SHEET = "EQUATION_AND_FORMULA_SHEET", "Equation and formula sheet"
    DIAGRAM_AND_CONCEPT_MAP = "DIAGRAM_AND_CONCEPT_MAP", "Diagram and concept map"
    FLASHCARDS_AND_SCRATCHPAD = "FLASHCARDS_AND_SCRATCHPAD", "Flashcards and scratchpad"
    CODE_ARTIFACT = "CODE_ARTIFACT", "Code artefact"


class StudyScaffoldGenerationStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    VALIDATING = "VALIDATING", "Validating"
    READY = "READY", "Ready"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
