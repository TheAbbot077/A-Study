from __future__ import annotations

from apps.learning_journeys.management.commands.synchronize_learning_journeys import Command as SynchronizeCommand


class Command(SynchronizeCommand):
    help = "Rebuild learning journey projections by re-running the canonical synchronization service."

