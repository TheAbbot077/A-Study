from __future__ import annotations

import hashlib
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from .experience_services import LearningStudioExperienceService
from .tutor_session_services import TutorSessionOpeningReadiness, TutorSessionOpeningService


class TeachingRuntimeReadiness:
    READY = "READY"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


class TeachingStepType:
    OPENING = "OPENING"
    RECAP = "RECAP"
    TEACH = "TEACH"
    EXAMPLE = "EXAMPLE"
    VISUAL = "VISUAL"
    SOCRATIC_PROMPT = "SOCRATIC_PROMPT"
    CONCEPT_CHECK = "CONCEPT_CHECK"
    REFLECTION = "REFLECTION"
    SUMMARY = "SUMMARY"
    NEXT_STEP = "NEXT_STEP"


EXPLANATION_MODES = {
    "SIMPLE": "Explain simply",
    "VISUAL": "Explain visually",
    "ACADEMIC": "Explain academically",
    "EXAM_FOCUSED": "Explain for exams",
    "ANALOGY": "Use an analogy",
    "EXAMPLES": "Use examples",
    "MATHEMATICAL": "Use mathematical steps",
}


class IntelligentTeachingExperienceService:
    def __init__(
        self,
        *,
        opening_service: TutorSessionOpeningService | None = None,
        studio_service: LearningStudioExperienceService | None = None,
    ):
        self.opening_service = opening_service or TutorSessionOpeningService()
        self.studio_service = studio_service or LearningStudioExperienceService()

    def session(self, *, workspace_id, actor) -> dict[str, Any]:
        opening = self.opening_service.execute(workspace_id=workspace_id, actor=actor)
        studio = self.studio_service.experience(workspace_id=workspace_id, actor=actor)
        runtime = self._runtime(opening=opening, studio=studio)
        return {
            "workspace_id": str(workspace_id),
            "opening": opening,
            "studio": studio,
            "runtime": runtime,
            "explanation_modes": self._explanation_modes(opening),
            "safety": {
                "mastery_claims_permitted": False,
                "frontend_may_create_academic_claims": False,
                "raw_transcript_mining_permitted": False,
            },
        }

    def start(self, *, workspace_id, actor) -> dict[str, Any]:
        self.studio_service.start(workspace_id=workspace_id, actor=actor)
        return self.session(workspace_id=workspace_id, actor=actor)

    def explanation_mode(self, *, workspace_id, actor, mode: str) -> dict[str, Any]:
        mode = mode.upper().strip()
        if mode not in EXPLANATION_MODES:
            raise ValidationError("Unsupported explanation mode.", code="EXPLANATION_MODE_UNSUPPORTED")
        opening = self.opening_service.execute(workspace_id=workspace_id, actor=actor)
        destination = opening.get("current_destination")
        if not destination:
            return {
                "mode": mode,
                "label": EXPLANATION_MODES[mode],
                "status": "BLOCKED",
                "explanation": "Abbot needs a governed study-plan destination before changing explanation style.",
                "source_references": [],
                "warning_codes": ["CURRENT_DESTINATION_UNAVAILABLE"],
            }
        warning_codes: list[str] = []
        if mode == "MATHEMATICAL" and destination.get("node_type") not in {"CONCEPT", "COMPETENCY", "ASSESSMENT_OBJECTIVE"}:
            warning_codes.append("EXPLANATION_MODE_PARTIAL_FIT")
        return {
            "mode": mode,
            "label": EXPLANATION_MODES[mode],
            "status": "READY",
            "explanation": self._mode_copy(mode=mode, title=destination["title"]),
            "source_concept": self._destination_label(destination),
            "source_references": self._source_references(opening),
            "warning_codes": warning_codes,
            "guardrails": [
                "Explanation mode changes presentation, not curriculum authority.",
                "Generated wording does not replace governed sources.",
            ],
        }

    def respond(
        self,
        *,
        workspace_id,
        actor,
        response_text: str,
        interaction_type: str = "SOCRATIC_PROMPT",
        idempotency_key: str = "",
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        response_text = response_text.strip()
        if not response_text:
            raise ValidationError("A learner response is required.", code="LEARNER_RESPONSE_REQUIRED")
        if len(response_text) > 4000:
            raise ValidationError("Learner response is too long.", code="LEARNER_RESPONSE_TOO_LONG")

        opening = self.opening_service.execute(workspace_id=workspace_id, actor=actor)
        studio = self.studio_service.experience(workspace_id=workspace_id, actor=actor)
        receipt_id = self._receipt_id(workspace_id=workspace_id, response_text=response_text, interaction_type=interaction_type)
        recorded_turn = None
        if studio.get("can_send_message") and idempotency_key and isinstance(expected_version, int):
            recorded_turn = self.studio_service.submit_turn(
                workspace_id=workspace_id,
                actor=actor,
                text=response_text,
                idempotency_key=idempotency_key,
                expected_version=expected_version,
            )
            receipt_id = recorded_turn["turn_id"]
        disposition = "READY_FOR_CONCEPT_CHECK" if interaction_type == "SOCRATIC_PROMPT" else "READY_TO_CONTINUE"
        if len(response_text.split()) < 3:
            disposition = "CLARIFICATION_REQUESTED"
        return {
            "receipt_id": receipt_id,
            "workspace_id": str(workspace_id),
            "interaction_type": interaction_type,
            "disposition": disposition,
            "learner_safe_feedback": self._feedback(disposition),
            "evidence_reference": {
                "kind": "TEACHING_TURN" if recorded_turn else "TEACHING_INTERACTION_RECEIPT",
                "recorded": bool(recorded_turn),
                "reference": receipt_id,
            },
            "source_concept": self._destination_label(opening.get("current_destination")),
            "mastery_awarded": False,
            "identity_write_performed": False,
        }

    def complete(self, *, workspace_id, actor) -> dict[str, Any]:
        opening = self.opening_service.execute(workspace_id=workspace_id, actor=actor)
        studio = self.studio_service.experience(workspace_id=workspace_id, actor=actor)
        runtime = self._runtime(opening=opening, studio=studio)
        destination = opening.get("current_destination")
        title = destination["title"] if destination else opening["workspace_summary"]["display_name"]
        completed_steps = [step["step_id"] for step in runtime["steps"] if step["status"] != "BLOCKED"]
        return {
            "session_id": studio.get("teaching_session_id") or "",
            "workspace_id": str(workspace_id),
            "completed_steps": completed_steps,
            "concepts_covered": [self._destination_label(destination)] if destination else [],
            "learner_safe_summary": f"Today we worked on {title}. This is a teaching-session summary, not a mastery decision.",
            "can_now_statements": [
                f"You can try explaining the main idea of {title} in your own words.",
                "You can ask Abbot for another example or continue to the next checkpoint.",
            ],
            "next_recommended_step": runtime["next_step"],
            "evidence_receipts": [],
            "motivation_items": [
                "You kept your study plan moving.",
                "You completed a focused teaching segment.",
            ],
            "guardrails": [
                "No mastery, credit, grade, or certification was awarded.",
                "Session closure does not update Learning Identity from raw responses.",
            ],
            "created_at": timezone.now().isoformat(),
        }

    def _runtime(self, *, opening: dict[str, Any], studio: dict[str, Any]) -> dict[str, Any]:
        destination = opening.get("current_destination")
        blockers = list(dict.fromkeys(opening.get("blocker_codes", []) + studio.get("blocker_codes", [])))
        readiness = self._readiness(opening=opening, blockers=blockers, destination=destination)
        title = destination["title"] if destination else opening["workspace_summary"]["display_name"]
        steps = self._steps(opening=opening, readiness=readiness, title=title)
        return {
            "runtime_id": self._runtime_id(opening["workspace_id"], title),
            "readiness": readiness,
            "current_destination": destination,
            "steps": steps,
            "source_references": self._source_references(opening),
            "blocker_codes": blockers,
            "warning_codes": opening.get("warning_codes", []),
            "next_step": "Resolve blockers" if readiness == TeachingRuntimeReadiness.BLOCKED else "Continue to the guided question",
        }

    def _readiness(self, *, opening: dict[str, Any], blockers: list[str], destination: dict[str, Any] | None) -> str:
        if opening["readiness"] == TutorSessionOpeningReadiness.BLOCKED or not destination:
            return TeachingRuntimeReadiness.BLOCKED
        if blockers or opening["readiness"] == TutorSessionOpeningReadiness.PARTIAL:
            return TeachingRuntimeReadiness.PARTIAL
        return TeachingRuntimeReadiness.READY

    def _steps(self, *, opening: dict[str, Any], readiness: str, title: str) -> list[dict[str, Any]]:
        if readiness == TeachingRuntimeReadiness.BLOCKED:
            return [
                self._step(1, TeachingStepType.OPENING, "Open session", opening["opening_message"], status="BLOCKED"),
                self._step(2, TeachingStepType.NEXT_STEP, "Next safe action", "Review the study-plan blockers before teaching continues.", status="BLOCKED"),
            ]
        prior = opening.get("previous_activity_summary")
        return [
            self._step(1, TeachingStepType.OPENING, "Open session", opening["opening_message"]),
            self._step(2, TeachingStepType.RECAP, "Quick recap", prior["summary"] if prior else "We will begin with a short orientation before teaching."),
            self._step(3, TeachingStepType.TEACH, "Teach the idea", f"Abbot will teach {title} from the governed study plan and available sources."),
            self._step(4, TeachingStepType.EXAMPLE, "Work an example", f"Use one source-grounded example or application for {title}."),
            {
                **self._step(5, TeachingStepType.VISUAL, "Whiteboard", f"Build a simple visual map for {title}."),
                "whiteboard_artifact": self._whiteboard(title),
            },
            {
                **self._step(6, TeachingStepType.SOCRATIC_PROMPT, "Guided question", "Try explaining this part back in one sentence."),
                "prompt": {"input_type": "SHORT_TEXT", "placeholder": "Write one sentence in your own words."},
            },
            {
                **self._step(7, TeachingStepType.CONCEPT_CHECK, "Concept check", f"Checkpoint: what is the most important idea in {title}?"),
                "concept_check": {"type": "EXPLAIN_BACK", "allowed_response_format": "SHORT_RESPONSE"},
            },
            self._step(8, TeachingStepType.SUMMARY, "Summary", "Close with what was covered and what comes next."),
            self._step(9, TeachingStepType.NEXT_STEP, "Next step", "Continue, review, or prepare for the next concept check."),
        ]

    def _step(self, ordinal: int, step_type: str, title: str, body: str, *, status: str = "READY") -> dict[str, Any]:
        return {
            "step_id": f"step-{ordinal}",
            "ordinal": ordinal,
            "type": step_type,
            "title": title,
            "body": body,
            "status": status,
            "learner_safe_label": title,
        }

    def _whiteboard(self, title: str) -> dict[str, Any]:
        return {
            "artifact_id": self._runtime_id("whiteboard", title),
            "type": "CONCEPT_MAP",
            "title": f"{title} map",
            "description": "A structured map for the current concept. It is a teaching aid, not a new source of authority.",
            "nodes": [
                {"id": "current", "label": title},
                {"id": "example", "label": "Example"},
                {"id": "question", "label": "Guided question"},
            ],
            "edges": [
                {"from": "current", "to": "example", "label": "shown through"},
                {"from": "current", "to": "question", "label": "checked by"},
            ],
            "rendering_hints": {"layout": "simple-map"},
            "safety_status": "SAFE",
        }

    def _explanation_modes(self, opening: dict[str, Any]) -> list[dict[str, Any]]:
        has_destination = bool(opening.get("current_destination"))
        return [
            {"mode": mode, "label": label, "available": has_destination}
            for mode, label in EXPLANATION_MODES.items()
        ]

    def _mode_copy(self, *, mode: str, title: str) -> str:
        if mode == "SIMPLE":
            return f"Let's break {title} into smaller pieces and keep each step clear."
        if mode == "VISUAL":
            return f"Let's use the whiteboard map to see how the parts of {title} connect."
        if mode == "ACADEMIC":
            return f"Let's use precise terms for {title} while staying with the governed source."
        if mode == "EXAM_FOCUSED":
            return f"Let's focus on how {title} is commonly checked, without claiming this is an exam result."
        if mode == "ANALOGY":
            return f"Let's use a careful analogy for {title}, and treat it as a teaching aid rather than proof."
        if mode == "EXAMPLES":
            return f"Let's add another governed example for {title}."
        return f"Let's represent {title} as ordered steps where that is appropriate."

    def _feedback(self, disposition: str) -> str:
        return {
            "CLARIFICATION_REQUESTED": "Thanks — give me a little more detail and we can keep going.",
            "READY_FOR_CONCEPT_CHECK": "Good direction. Let's use a concept check next, without treating this as mastery.",
            "READY_TO_CONTINUE": "Response received. You are ready to continue the teaching sequence.",
        }.get(disposition, "Response received.")

    def _source_references(self, opening: dict[str, Any]) -> list[dict[str, str]]:
        destination = opening.get("current_destination")
        if not destination:
            return []
        return [
            {
                "label": destination["title"],
                "kind": destination.get("node_type", "CONCEPT"),
                "state": destination.get("status", "PLANNED"),
            }
        ]

    def _destination_label(self, destination: dict[str, Any] | None) -> dict[str, str]:
        if not destination:
            return {"title": "", "type": "", "state": "UNAVAILABLE"}
        return {
            "title": str(destination.get("title", "")),
            "type": str(destination.get("node_type", "")),
            "state": str(destination.get("status", "")),
        }

    def _runtime_id(self, *parts: str) -> str:
        return hashlib.sha256(":".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:24]

    def _receipt_id(self, *, workspace_id, response_text: str, interaction_type: str) -> str:
        digest = hashlib.sha256(f"{workspace_id}:{interaction_type}:{response_text}".encode("utf-8")).hexdigest()[:24]
        return f"receipt-{digest}"
