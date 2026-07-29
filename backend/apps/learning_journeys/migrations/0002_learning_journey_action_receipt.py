import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_alter_institution_institution_type_and_more"),
        ("learning_journeys", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningJourneyActionReceipt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action_code", models.CharField(max_length=64)),
                ("idempotency_key", models.CharField(blank=True, max_length=128)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACCEPTED", "Accepted"),
                            ("SUCCEEDED", "Succeeded"),
                            ("FAILED", "Failed"),
                            ("REJECTED", "Rejected"),
                            ("NO_OP", "No-op"),
                        ],
                        default="ACCEPTED",
                        max_length=16,
                    ),
                ),
                ("source_capability", models.CharField(blank=True, max_length=96)),
                ("source_record_id", models.UUIDField(blank=True, null=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_code", models.CharField(blank=True, max_length=96)),
                ("failure_message", models.CharField(blank=True, max_length=500)),
                ("request_metadata", models.JSONField(blank=True, default=dict)),
                ("result_metadata", models.JSONField(blank=True, default=dict)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="learning_journey_action_receipts",
                        to="users.user",
                    ),
                ),
                (
                    "journey",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="action_receipts",
                        to="learning_journeys.learningjourney",
                    ),
                ),
            ],
            options={"db_table": "learning_journey_action_receipt"},
        ),
        migrations.AddIndex(
            model_name="learningjourneyactionreceipt",
            index=models.Index(fields=["journey", "action_code", "status"], name="lj_receipt_action_status_idx"),
        ),
        migrations.AddIndex(
            model_name="learningjourneyactionreceipt",
            index=models.Index(fields=["actor", "started_at"], name="lj_receipt_actor_time_idx"),
        ),
        migrations.AddConstraint(
            model_name="learningjourneyactionreceipt",
            constraint=models.UniqueConstraint(
                fields=("journey", "action_code", "idempotency_key"),
                condition=~Q(idempotency_key=""),
                name="lj_action_receipt_idempotency_unique",
            ),
        ),
    ]
