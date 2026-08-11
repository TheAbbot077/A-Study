import pytest

from apps.study_lab.domain.enums import ProviderContext, ToolAvailabilityReasonCode
from apps.study_lab.infrastructure.adapters import ProviderAdapterRegistry


@pytest.mark.django_db
@pytest.mark.parametrize("provider", [ProviderContext.ABBOT, ProviderContext.ARIEL, ProviderContext.WHITEBOARD, ProviderContext.RESOURCE, ProviderContext.CONCEPT_CHECK, ProviderContext.PROGRESS, ProviderContext.JOURNEY])
def test_providers_fail_closed(provider):
    adapter = ProviderAdapterRegistry.get_adapter(provider)
    reason_code, detail = adapter.evaluate_availability(None, None)
    assert reason_code == ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE
    assert "not implemented" in detail
