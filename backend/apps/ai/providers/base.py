from abc import ABC, abstractmethod

from apps.ai.orchestration.types import AIRequest, AIResponse


class AIProvider(ABC):
    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError
