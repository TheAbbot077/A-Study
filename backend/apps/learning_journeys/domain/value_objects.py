from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StatusReason:
    code: str
    message: str = ""

    def to_dict(self) -> dict:
        payload = {"code": self.code}
        if self.message:
            payload["message"] = self.message
        return payload


@dataclass(frozen=True)
class CurrentStep:
    code: str
    title: str
    description: str
    sequence: int

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "sequence": self.sequence,
        }


@dataclass(frozen=True)
class AvailableAction:
    code: str
    label: str
    method: str = "POST"
    endpoint_name: str = ""
    enabled: bool = True
    disabled_reason: str = ""
    requires_confirmation: bool = False

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "method": self.method,
            "endpoint_name": self.endpoint_name,
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason,
            "requires_confirmation": self.requires_confirmation,
        }


@dataclass(frozen=True)
class JourneyBlocker:
    code: str
    category: str
    message: str
    recoverable: bool
    blocking_capability: str
    resolution_action_code: str = ""

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "category": self.category,
            "message": self.message,
            "recoverable": self.recoverable,
            "blocking_capability": self.blocking_capability,
            "resolution_action_code": self.resolution_action_code,
        }


@dataclass(frozen=True)
class JourneyProjection:
    status: str
    status_reason: StatusReason
    current_step: CurrentStep
    available_actions: tuple[AvailableAction, ...] = ()
    blockers: tuple[JourneyBlocker, ...] = ()
    capability_references: dict = field(default_factory=dict)
    subject: dict | None = None
    authority: dict | None = None

    def to_dict(self) -> dict:
        return {
            "state": self.status,
            "status_reason": self.status_reason.to_dict(),
            "current_step": self.current_step.to_dict(),
            "available_actions": [action.to_dict() for action in self.available_actions],
            "blockers": [blocker.to_dict() for blocker in self.blockers],
            "capability_references": dict(self.capability_references),
            "subject": self.subject,
            "authority": self.authority,
        }
