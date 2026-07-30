from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from apps.users.domain.models import User

from ..domain.enums import LearningJourneySourceType
from ..domain.models import LearningJourneySourceBinding
from .services import CreateLearningJourneyService


@dataclass(frozen=True)
class BackfillSummary:
    processed: int = 0
    created: int = 0
    unchanged: int = 0
    failed: int = 0
    failures: tuple[dict, ...] = ()
    dry_run: bool = True

    def to_dict(self) -> dict:
        return {
            "processed": self.processed,
            "created": self.created,
            "unchanged": self.unchanged,
            "failed": self.failed,
            "failures": list(self.failures),
            "dry_run": self.dry_run,
        }


class LearningJourneyBackfillService:
    def backfill_self_study_workspaces(self, *, actor: User, limit: int = 100, dry_run: bool = True, tenant_id=None) -> dict:
        if not actor.is_superuser and not actor.is_staff:
            raise PermissionDenied("LEARNING_JOURNEY_BACKFILL_PERMISSION_DENIED")
        from apps.self_study.workspace_models import SelfStudyWorkspace

        bound_ids = LearningJourneySourceBinding.objects.filter(source_type=LearningJourneySourceType.SELF_STUDY_WORKSPACE).values_list("source_id", flat=True)
        queryset = SelfStudyWorkspace.objects.select_related("learner", "tenant").exclude(id__in=list(bound_ids)).order_by("created_at", "id")
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        processed = created = unchanged = failed = 0
        failures: list[dict] = []
        service = CreateLearningJourneyService()
        for workspace in queryset[:limit]:
            processed += 1
            if dry_run:
                unchanged += 1
                continue
            try:
                service.for_self_study_workspace(workspace_id=workspace.id, actor=workspace.learner)
                created += 1
            except Exception as exc:  # pragma: no cover - operator report path
                failed += 1
                failures.append({"source_type": "SELF_STUDY_WORKSPACE", "source_id": str(workspace.id), "code": type(exc).__name__})
        return BackfillSummary(
            processed=processed,
            created=created,
            unchanged=unchanged,
            failed=failed,
            failures=tuple(failures),
            dry_run=dry_run,
        ).to_dict()
