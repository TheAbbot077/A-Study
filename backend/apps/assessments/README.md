# PI-8D.9 Recovery Hardening Notes

PI-8D.9 keeps the canonical academic chain intact and adds release hardening
around recovery orchestration.

Canonical recovery authority:

- `RecoveryObservationService` in `apps.assessments.services.recovery_service`
- `ReconcileLearningRecoveryService` in `apps.assessments.services.recovery_reconciliation_service`

Compatibility note:

- `learning_journey.recovery_started`
- `learning_journey.recovery_completed`

These event names remain registered for historical consumers, but the
PI-8D.9 recovery projection/reconciliation path is the canonical recovery
hardening surface.

Legacy-path note:

- Recovery should be observed and reconciled through the assessments
  recovery services.
- No new duplicate recovery engine should be introduced alongside these
  services.
