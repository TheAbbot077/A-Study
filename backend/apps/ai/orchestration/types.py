from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AIRequest:
    task_name: str
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResponse:
    text: str
    provider_name: str
    model_name: str
    metadata: dict[str, Any] = field(default_factory=dict)
