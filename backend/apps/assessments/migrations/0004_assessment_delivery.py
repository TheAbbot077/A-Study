import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("assessments", "0003_item_bank"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssessmentDeliverySession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("created", "Created"), ("active", "Active"), ("paused", "Paused"), ("submitted", "Submitted"), ("completed", "Completed"), ("abandoned", "Abandoned")], default="created", max_length=50)),
                ("current_sequence_number", models.PositiveIntegerField(default=1)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="delivery_sessions", to="assessments.assessment")),
                ("assessment_attempt", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="delivery_sessions", to="assessments.assessmentattempt")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessment_delivery_sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "assessment_delivery_session",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="assessmentdeliverysession",
            index=models.Index(fields=["assessment"], name="delivery_session_assess_idx"),
        ),
        migrations.AddIndex(
            model_name="assessmentdeliverysession",
            index=models.Index(fields=["learner"], name="delivery_session_learner_idx"),
        ),
        migrations.AddIndex(
            model_name="assessmentdeliverysession",
            index=models.Index(fields=["status"], name="delivery_session_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="assessmentdeliverysession",
            constraint=models.CheckConstraint(condition=models.Q(("current_sequence_number__gte", 1)), name="assessment_delivery_current_sequence_gte_1"),
        ),
    ]
