import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("academic", "0006_content_review_fields"),
        ("assessments", "0006_evidence_integration_source"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RemediationPlan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("active", "Active"), ("completed", "Completed"), ("escalated", "Escalated"), ("cancelled", "Cancelled"), ("closed", "Closed")], default="pending", max_length=50)),
                ("rationale", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("escalated_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("content_concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="remediation_plans", to="academic.contentconcept")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="remediation_plans", to=settings.AUTH_USER_MODEL)),
                ("trigger_evidence", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="triggered_remediation_plans", to="assessments.learningevidence")),
            ],
            options={
                "db_table": "remediation_plan",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RemediationRecommendation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("recommendation_type", models.CharField(choices=[("review_lesson", "Review Lesson"), ("repeat_activity", "Repeat Activity"), ("teach_ariel", "Teach Ariel"), ("additional_questions", "Additional Questions"), ("read_source_material", "Read Source Material"), ("simulation", "Simulation"), ("educator_review", "Educator Review"), ("practice_assessment", "Practice Assessment"), ("programming_task", "Programming Task"), ("custom", "Custom")], max_length=100)),
                ("title", models.CharField(max_length=255)),
                ("rationale", models.TextField(blank=True)),
                ("priority", models.PositiveIntegerField(default=1)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recommendations", to="remediation.remediationplan")),
            ],
            options={
                "db_table": "remediation_recommendation",
                "ordering": ["priority", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="RemediationActivity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("activity_type", models.CharField(choices=[("lesson_replay", "Lesson Replay"), ("practice_assessment", "Practice Assessment"), ("simulation", "Simulation"), ("teach_ariel", "Teach Ariel"), ("programming_task", "Programming Task"), ("educator_review", "Educator Review"), ("custom", "Custom")], max_length=100)),
                ("title", models.CharField(max_length=255)),
                ("instructions", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="planned", max_length=50)),
                ("evidence_producer_type", models.CharField(blank=True, max_length=100)),
                ("evidence_reference_id", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activities", to="remediation.remediationplan")),
                ("recommendation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activities", to="remediation.remediationrecommendation")),
                ("resource", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="remediation_activities", to="academic.learningresource")),
            ],
            options={
                "db_table": "remediation_activity",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="RemediationAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("started", "Started"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="started", max_length=50)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("activity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="remediation.remediationactivity")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="remediation_attempts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "remediation_attempt",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RemediationOutcome",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("outcome", models.CharField(choices=[("improved", "Improved"), ("unchanged", "Unchanged"), ("regressed", "Regressed"), ("escalated", "Escalated")], max_length=50)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("recorded_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("activity", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="outcomes", to="remediation.remediationactivity")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outcomes", to="remediation.remediationplan")),
                ("supporting_evidence", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="remediation_outcomes", to="assessments.learningevidence")),
            ],
            options={
                "db_table": "remediation_outcome",
                "ordering": ["-recorded_at"],
            },
        ),
        migrations.AddIndex(model_name="remediationplan", index=models.Index(fields=["learner"], name="rem_plan_learner_idx")),
        migrations.AddIndex(model_name="remediationplan", index=models.Index(fields=["content_concept"], name="rem_plan_concept_idx")),
        migrations.AddIndex(model_name="remediationplan", index=models.Index(fields=["status"], name="rem_plan_status_idx")),
        migrations.AddConstraint(model_name="remediationrecommendation", constraint=models.CheckConstraint(condition=models.Q(("priority__gte", 1)), name="rem_recommendation_priority_gte_1")),
        migrations.AddIndex(model_name="remediationactivity", index=models.Index(fields=["activity_type"], name="rem_activity_type_idx")),
        migrations.AddIndex(model_name="remediationactivity", index=models.Index(fields=["status"], name="rem_activity_status_idx")),
    ]
