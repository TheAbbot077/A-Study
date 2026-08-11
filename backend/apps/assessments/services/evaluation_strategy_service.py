from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.assessments.domain.models import AssessmentItem, AssessmentItemType, AssessmentResponse


@dataclass(frozen=True)
class ResolvedEvaluationStrategy:
    strategy_code: str
    strategy_version: str
    evaluator_type: str
    answer_contract_reference: str
    answer_contract_version: str
    answer_contract_checksum: str


class ResolveEvaluationStrategyService:
    STRATEGY_VERSION = "1"

    def resolve(self, *, item: AssessmentItem, response: AssessmentResponse) -> ResolvedEvaluationStrategy:
        if item.item_type == AssessmentItemType.TRUE_FALSE:
            return self._strategy("EXACT_BOOLEAN_MATCH", item)
        if item.item_type == AssessmentItemType.MULTIPLE_CHOICE:
            return self._strategy("EXACT_OPTION_MATCH", item)
        if item.item_type == AssessmentItemType.CALCULATION:
            return self._strategy("NUMERIC_EXACT", item)
        return self._strategy("NOT_EVALUABLE", item)

    def _strategy(self, strategy_code: str, item: AssessmentItem) -> ResolvedEvaluationStrategy:
        contract = self._answer_contract(item)
        return ResolvedEvaluationStrategy(
            strategy_code=strategy_code,
            strategy_version=self.STRATEGY_VERSION,
            evaluator_type="deterministic",
            answer_contract_reference=contract["reference"],
            answer_contract_version=contract["version"],
            answer_contract_checksum=contract["checksum"],
        )

    def _answer_contract(self, item: AssessmentItem) -> dict[str, str]:
        metadata = item.metadata or {}
        checksum = str(sorted(metadata.items()))
        return {
            "reference": f"assessment_item:{item.id}",
            "version": "1",
            "checksum": checksum,
        }
