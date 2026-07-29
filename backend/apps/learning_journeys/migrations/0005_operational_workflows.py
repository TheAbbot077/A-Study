from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("learning_journeys", "0004_institutional_orchestration"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="learningjourneyactionreceipt",
            name="status",
            field=models.CharField(
                choices=[
                    ("ACCEPTED", "Accepted"),
                    ("SUCCEEDED", "Succeeded"),
                    ("FAILED", "Failed"),
                    ("REJECTED", "Rejected"),
                    ("NO_OP", "No-op"),
                    ("CONFLICT", "Conflict"),
                ],
                default="ACCEPTED",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="LearningJourneyOperation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action_code", models.CharField(max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("SUCCEEDED", "Succeeded"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("progress_phase", models.CharField(blank=True, max_length=96)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_code", models.CharField(blank=True, max_length=96)),
                ("failure_message", models.CharField(blank=True, max_length=500)),
                ("result_reference", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_journey_operations", to=settings.AUTH_USER_MODEL)),
                ("journey", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="operations", to="learning_journeys.learningjourney")),
                (
                    "receipt",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="operations",
                        to="learning_journeys.learningjourneyactionreceipt",
                    ),
                ),
            ],
            options={"db_table": "learning_journey_operation"},
        ),
        migrations.CreateModel(
            name="LearningJourneyIntegrityFinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "code",
                    models.CharField(
                        choices=[
                            ("MISSING_SOURCE_BINDING", "Missing source binding"),
                            ("DUPLICATE_ACTIVE_SUBJECT_BINDING", "Duplicate active subject binding"),
                            ("JOURNEY_SOURCE_LEARNER_MISMATCH", "Journey source learner mismatch"),
                            ("JOURNEY_INSTITUTION_MISMATCH", "Journey institution mismatch"),
                            ("INVALID_ACTIVE_SESSION_REFERENCE", "Invalid active session reference"),
                            ("INVALID_PLAN_REFERENCE", "Invalid plan reference"),
                            ("STALE_AUTHORITY_PROJECTION", "Stale authority projection"),
                            ("PROJECTION_VERSION_MISMATCH", "Projection version mismatch"),
                            ("TERMINAL_JOURNEY_WITH_ACTIVE_OPERATION", "Terminal journey with active operation"),
                            ("INSTITUTIONAL_JOURNEY_WITHOUT_ACTIVE_AUTHORITY", "Institutional journey without active authority"),
                            ("SELF_STUDY_JOURNEY_WITH_INSTITUTIONAL_AUTHORITY", "Self-study journey with institutional authority"),
                        ],
                        max_length=96,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[("INFO", "Info"), ("WARNING", "Warning"), ("BLOCKING", "Blocking"), ("CRITICAL", "Critical")],
                        default="WARNING",
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("OPEN", "Open"), ("ACKNOWLEDGED", "Acknowledged"), ("RESOLVED", "Resolved"), ("DISMISSED", "Dismissed")],
                        default="OPEN",
                        max_length=16,
                    ),
                ),
                ("message", models.CharField(max_length=500)),
                ("source_capability", models.CharField(blank=True, max_length=96)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("detected_at", models.DateTimeField(auto_now_add=True)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("resolution", models.CharField(blank=True, max_length=500)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("journey", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="integrity_findings", to="learning_journeys.learningjourney")),
            ],
            options={"db_table": "learning_journey_integrity_finding"},
        ),
        migrations.AddIndex(
            model_name="learningjourneyoperation",
            index=models.Index(fields=["journey", "status"], name="lj_operation_status_idx"),
        ),
        migrations.AddIndex(
            model_name="learningjourneyoperation",
            index=models.Index(fields=["journey", "action_code"], name="lj_operation_action_idx"),
        ),
        migrations.AddIndex(
            model_name="learningjourneyoperation",
            index=models.Index(fields=["actor", "started_at"], name="lj_operation_actor_time_idx"),
        ),
        migrations.AddIndex(
            model_name="learningjourneyintegrityfinding",
            index=models.Index(fields=["journey", "status"], name="lj_integrity_status_idx"),
        ),
        migrations.AddIndex(
            model_name="learningjourneyintegrityfinding",
            index=models.Index(fields=["journey", "code"], name="lj_integrity_code_idx"),
        ),
        migrations.AddConstraint(
            model_name="learningjourneyintegrityfinding",
            constraint=models.UniqueConstraint(
                fields=("journey", "code"),
                condition=Q(status="OPEN"),
                name="lj_integrity_one_open_code",
            ),
        ),
    ]
