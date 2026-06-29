from apps.ai.orchestration.types import AIRequest, AIResponse
from apps.ai.providers.base import AIProvider


class AIOrchestrator:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def generate(self, request: AIRequest) -> AIResponse:
        return self.provider.generate(request)
