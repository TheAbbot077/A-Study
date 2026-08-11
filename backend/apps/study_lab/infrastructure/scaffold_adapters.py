from __future__ import annotations


class _UnavailableStudyScaffoldGenerationProvider:
    provider_name = "STUDY_LAB"

    def evaluate_availability(self, workspace, generation_type, source_artefacts):
        return False, "SCAFFOLD_PROVIDER_UNAVAILABLE", f"{self.provider_name} scaffold generation is not implemented in PI-8C.9"

    def generate(self, workspace, learner_id, generation_type, source_artefacts, *, requested_artefact_type, title="", summary="", native_payload=None, policy_version="1", idempotency_key="", request=None):
        raise RuntimeError(f"{self.provider_name} scaffold generation is not implemented in PI-8C.9")


class DeterministicStudyScaffoldGenerationProvider:
    def __init__(self):
        self.generate_calls = 0

    def evaluate_availability(self, workspace, generation_type, source_artefacts):
        return True, "SCAFFOLD_PROVIDER_AVAILABLE", "available"

    def generate(self, workspace, learner_id, generation_type, source_artefacts, *, requested_artefact_type, title="", summary="", native_payload=None, policy_version="1", idempotency_key="", request=None):
        self.generate_calls += 1
        payload = native_payload or {}
        payload.setdefault("generation_type", generation_type)
        payload.setdefault("source_artefact_ids", [str(item.id) for item in source_artefacts])
        payload.setdefault("policy_version", policy_version)
        return {
            "provider_reference": f"scaffold:{generation_type}:{self.generate_calls}",
            "title": title or f"Generated {requested_artefact_type}",
            "summary": summary or f"Deterministic scaffold for {generation_type}",
            "native_payload": payload,
            "schema_version": "1",
        }


class ScaffoldGenerationProviderRegistry:
    _providers = {
        "STUDY_LAB": _UnavailableStudyScaffoldGenerationProvider(),
    }

    @classmethod
    def get_provider(cls, provider_context):
        return cls._providers.get(provider_context, _UnavailableStudyScaffoldGenerationProvider())

    @classmethod
    def register_provider(cls, provider_context, provider):
        cls._providers[provider_context] = provider

    @classmethod
    def reset_provider(cls, provider_context):
        cls._providers[provider_context] = _UnavailableStudyScaffoldGenerationProvider()
