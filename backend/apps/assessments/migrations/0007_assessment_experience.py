import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0006_evidence_integration_source"),
        ("academic", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssessmentExperience",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("learning_journey_id", models.UUIDField(blank=True, null=True)),
                ("institution_id", models.UUIDField(blank=True, null=True)),
                ("purpose", models.CharField(choices=[("entry_diagnostic", "Entry Diagnostic"), ("prerequisite_check", "Prerequisite Check"), ("concept_check", "Concept Check"), ("formative", "Formative"), ("practice", "Practice"), ("summative", "Summative"), ("remediation_check", "Remediation Check")], max_length=50)),
                ("state", models.CharField(choices=[("created", "Created"), ("ready", "Ready"), ("in_progress", "In Progress"), ("awaiting_response", "Awaiting Response"), ("submitted", "Submitted"), ("evaluating", "Evaluating"), ("evaluated", "Evaluated"), ("completed", "Completed"), ("cancelled", "Cancelled"), ("expired", "Expired"), ("failed", "Failed")], default="created", max_length=50)),
                ("assessment_strategy_type", models.CharField(blank=True, default="", max_length=50)),
                ("policy_version", models.CharField(default="1", max_length=64)),
                ("policy_snapshot", models.JSONField(blank=True, default=dict)),
                ("attempt_number", models.PositiveIntegerField(default=1)),
                ("blockers", models.JSONField(blank=True, default=list)),
                ("current_step", models.JSONField(blank=True, default=dict)),
                ("feedback_available", models.BooleanField(default=False)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("ready_at", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("evaluated_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("expired_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assessment_experiences", to="assessments.assessment")),
                ("assessment_attempt", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="experience", to="assessments.assessmentattempt")),
                ("content_concept", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assessment_experiences", to="academic.contentconcept")),
                ("delivery_session", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="experience", to="assessments.assessmentdeliverysession")),
                ("evaluation", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="experience", to="assessments.assessmentevaluation")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessment_experiences", to=settings.AUTH_USER_MODEL)),
                ("previous_experience", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="retry_experiences", to="assessments.assessmentexperience")),
            ],
            options={
                "db_table": "assessment_experience",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="assessmentexperience",
            index=models.Index(fields=["learner", "state"], name="assess_exp_learner_state_idx"),
        ),
        migrations.AddIndex(
            model_name="assessmentexperience",
            index=models.Index(fields=["assessment", "purpose"], name="assess_exp_assess_purpose_idx"),
        ),
        migrations.AddIndex(
            model_name="assessmentexperience",
            index=models.Index(fields=["learning_journey_id"], name="assess_exp_journey_idx"),
        ),
        migrations.AddConstraint(
            model_name="assessmentexperience",
            constraint=models.UniqueConstraint(condition=Q(state__in=["created", "ready", "in_progress", "awaiting_response", "submitted", "evaluating"]), fields=("learner", "assessment", "purpose"), name="assess_exp_unique_active_scope"),
        ),
    ]
