from __future__ import annotations

from apps.study_lab.domain.enums import ToolAvailabilityReasonCode


class _UnavailableAdapter:
    provider_name = ""

    def evaluate_availability(self, workspace, tool):
        return ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE, f"{self.provider_name} provider is not implemented in PI-8C.4"

    def invoke(self, workspace, tool, learner_id, **kwargs):
        raise RuntimeError(f"{self.provider_name} provider is not implemented in PI-8C.4")

    def project_session(self, session_id):
        return {"status": "provider_unavailable", "provider": self.provider_name, "session_id": str(session_id)}

    def project_journey(self, journey_id):
        return {"status": "provider_unavailable", "provider": self.provider_name, "journey_id": str(journey_id)}

    def project_progress(self, learner_id, workspace_id):
        return {"status": "provider_unavailable", "provider": self.provider_name, "workspace_id": str(workspace_id)}

    def project_resources(self, workspace):
        return {"status": "provider_unavailable", "provider": self.provider_name, "workspace_id": str(workspace.id)}

    def get_manifest(self):
        return {"status": "provider_unavailable", "provider": self.provider_name, "accepts": [], "produces": []}

    def validate_inputs(self, workspace, tool, input_artefacts):
        return False, ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE, f"{self.provider_name} provider is not implemented in PI-8C.5"

    def launch(self, workspace, tool, learner_id, **kwargs):
        raise RuntimeError(f"{self.provider_name} provider is not implemented in PI-8C.5")

    def resume(self, workspace, session, learner_id):
        raise RuntimeError(f"{self.provider_name} provider is not implemented in PI-8C.5")

    def import_artefact(self, workspace, learner_id, provider_reference):
        return {"metadata": {}, "schema_version": "1", "title": "", "summary": ""}

    def export_artefact(self, workspace, artefact, learner_id):
        return f"{self.provider_name.lower()}:{artefact.id}"

    def get_status(self, reference):
        return {"status": "provider_unavailable", "provider": self.provider_name, "reference": str(reference)}


class AbbotWorkspaceProvider(_UnavailableAdapter):
    provider_name = "ABBOT"


class ArielWorkspaceProvider(_UnavailableAdapter):
    provider_name = "ARIEL"


class WhiteboardWorkspaceProvider(_UnavailableAdapter):
    provider_name = "WHITEBOARD"


class ResourceWorkspaceProvider(_UnavailableAdapter):
    provider_name = "RESOURCE"


class ConceptCheckWorkspaceProvider(_UnavailableAdapter):
    provider_name = "CONCEPT_CHECK"


class ProgressWorkspaceProvider(_UnavailableAdapter):
    provider_name = "PROGRESS"


class JourneyWorkspaceProvider(_UnavailableAdapter):
    provider_name = "JOURNEY"


class ProviderAdapterRegistry:
    _adapters = {
        "ABBOT": AbbotWorkspaceProvider(),
        "ARIEL": ArielWorkspaceProvider(),
        "WHITEBOARD": WhiteboardWorkspaceProvider(),
        "RESOURCE": ResourceWorkspaceProvider(),
        "CONCEPT_CHECK": ConceptCheckWorkspaceProvider(),
        "PROGRESS": ProgressWorkspaceProvider(),
        "JOURNEY": JourneyWorkspaceProvider(),
    }

    @classmethod
    def get_adapter(cls, provider_context):
        return cls._adapters.get(provider_context)

    @classmethod
    def register_adapter(cls, provider_context, adapter):
        cls._adapters[provider_context] = adapter

    @classmethod
    def reset_adapter(cls, provider_context):
        cls._adapters.pop(provider_context, None)
