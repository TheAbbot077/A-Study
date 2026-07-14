from __future__ import annotations

from typing import Optional
import logging

from apps.assessment_review.domain.models import DifficultyCalibration
from apps.assessment_review.domain.repositories import CalibrationRepository
from apps.assessment_review.domain.services import RuleBasedDifficultyCalibrationPolicy
from apps.assessment_review.infrastructure.persistence import DjangoCalibrationRepository
from apps.assessments.domain.models import Assessment, ItemBankEntry, ItemDifficulty
from apps.core.exceptions import DomainValidationError
from apps.core.events import BusinessEvent, EventPublisher

logger = logging.getLogger(__name__)


class DifficultyCalibrationService:
    def __init__(
        self,
        calibration_repository: Optional[CalibrationRepository] = None,
        calibration_policy: Optional[RuleBasedDifficultyCalibrationPolicy] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.calibration_repository = calibration_repository or DjangoCalibrationRepository()
        self.calibration_policy = calibration_policy or RuleBasedDifficultyCalibrationPolicy()
        self.event_publisher = event_publisher or EventPublisher()

    def calibrate_item(
        self,
        item_bank_entry: ItemBankEntry,
        observed_success_rate: float | None,
        sample_size: int,
        assessment: Assessment | None = None,
        metadata: dict | None = None,
    ) -> DifficultyCalibration:
        if observed_success_rate is not None and not 0.0 <= observed_success_rate <= 1.0:
            raise DomainValidationError("Observed success rate must be between 0 and 1.")
        if sample_size < 0:
            raise DomainValidationError("Calibration sample_size must be greater than or equal to 0.")
        expected = getattr(item_bank_entry, "difficulty", ItemDifficulty.UNKNOWN)
        result = self.calibration_policy.calibrate(expected, observed_success_rate, sample_size)
        logger.info(
            "Calibrating assessment item difficulty: item_bank_entry_id=%s expected_difficulty=%s observed_success_rate=%s sample_size=%s direction=%s",
            item_bank_entry.id,
            expected,
            observed_success_rate,
            sample_size,
            result.direction,
        )
        calibration = self.calibration_repository.add(
            DifficultyCalibration(
                assessment=assessment,
                item_bank_entry=item_bank_entry,
                expected_difficulty=expected,
                observed_success_rate=observed_success_rate,
                sample_size=sample_size,
                calibrated_difficulty=result.calibrated_difficulty,
                direction=result.direction,
                calibration_reason=result.reason,
                metadata=metadata or {},
            )
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment_review.difficulty_calibrated",
                payload={
                    "difficulty_calibration_id": str(calibration.id),
                    "item_bank_entry_id": str(item_bank_entry.id),
                    "direction": calibration.direction,
                },
            )
        )
        return calibration

    def list_calibration_history_for_item(self, item_bank_entry: ItemBankEntry) -> list[DifficultyCalibration]:
        return self.calibration_repository.list_for_item(item_bank_entry)

    def list_recent_calibrations(self, limit: int = 100) -> list[DifficultyCalibration]:
        return self.calibration_repository.list_recent(limit=limit)
