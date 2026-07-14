from __future__ import annotations

from dataclasses import dataclass

from apps.assessment_review.domain.models import CalibrationDirection
from apps.assessments.domain.models import ItemDifficulty


DIFFICULTY_ORDER = [
    ItemDifficulty.EASY,
    ItemDifficulty.MEDIUM,
    ItemDifficulty.HARD,
    ItemDifficulty.ADVANCED,
]


@dataclass(frozen=True)
class DifficultyCalibrationResult:
    calibrated_difficulty: str
    direction: str
    reason: str


class RuleBasedDifficultyCalibrationPolicy:
    minimum_sample_size = 5

    def calibrate(self, expected_difficulty: str, observed_success_rate: float | None, sample_size: int) -> DifficultyCalibrationResult:
        if observed_success_rate is None or sample_size < self.minimum_sample_size:
            return DifficultyCalibrationResult(
                calibrated_difficulty=expected_difficulty,
                direction=CalibrationDirection.INSUFFICIENT_DATA,
                reason="Insufficient learner performance data for calibration.",
            )

        if observed_success_rate >= 0.85:
            return DifficultyCalibrationResult(
                calibrated_difficulty=self._shift(expected_difficulty, -1),
                direction=CalibrationDirection.EASIER_THAN_EXPECTED,
                reason="Learner success rate is high relative to expected difficulty.",
            )
        if observed_success_rate <= 0.45:
            return DifficultyCalibrationResult(
                calibrated_difficulty=self._shift(expected_difficulty, 1),
                direction=CalibrationDirection.HARDER_THAN_EXPECTED,
                reason="Learner success rate is low relative to expected difficulty.",
            )
        return DifficultyCalibrationResult(
            calibrated_difficulty=expected_difficulty,
            direction=CalibrationDirection.AS_EXPECTED,
            reason="Learner performance aligns with expected difficulty.",
        )

    def _shift(self, difficulty: str, delta: int) -> str:
        if difficulty not in DIFFICULTY_ORDER:
            return difficulty
        index = DIFFICULTY_ORDER.index(difficulty)
        return DIFFICULTY_ORDER[max(0, min(len(DIFFICULTY_ORDER) - 1, index + delta))]


__all__ = ["DifficultyCalibrationResult", "RuleBasedDifficultyCalibrationPolicy"]
