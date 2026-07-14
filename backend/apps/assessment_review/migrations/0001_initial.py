import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("assessments", "0006_evidence_integration_source"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AssessmentReview",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending_review", "Pending Review"), ("in_review", "In Review"), ("approved", "Approved"), ("needs_revision", "Needs Revision"), ("rejected", "Rejected"), ("archived", "Archived")], default="draft", max_length=50)),
                ("opened_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="assessments.assessment")),
                ("opened_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="opened_assessment_reviews", to=settings.AUTH_USER_MODEL)),
                ("reviewer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_assessment_reviews", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "assessment_review", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="QuestionReview",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending_review", "Pending Review"), ("in_review", "In Review"), ("approved", "Approved"), ("needs_revision", "Needs Revision"), ("rejected", "Rejected"), ("archived", "Archived")], default="draft", max_length=50)),
                ("opened_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("item_bank_entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="question_reviews", to="assessments.itembankentry")),
                ("opened_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="opened_question_reviews", to=settings.AUTH_USER_MODEL)),
                ("reviewer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_question_reviews", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "question_review", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DifficultyCalibration",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("expected_difficulty", models.CharField(choices=[("unknown", "Unknown"), ("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"), ("advanced", "Advanced")], default="unknown", max_length=50)),
                ("observed_success_rate", models.FloatField(blank=True, null=True)),
                ("sample_size", models.PositiveIntegerField(default=0)),
                ("calibrated_difficulty", models.CharField(choices=[("unknown", "Unknown"), ("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"), ("advanced", "Advanced")], default="unknown", max_length=50)),
                ("direction", models.CharField(choices=[("easier_than_expected", "Easier Than Expected"), ("as_expected", "As Expected"), ("harder_than_expected", "Harder Than Expected"), ("insufficient_data", "Insufficient Data")], default="insufficient_data", max_length=50)),
                ("calibration_reason", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assessment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="difficulty_calibrations", to="assessments.assessment")),
                ("item_bank_entry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="difficulty_calibrations", to="assessments.itembankentry")),
            ],
            options={"db_table": "difficulty_calibration", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="QualityFinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("finding_type", models.CharField(max_length=100)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="medium", max_length=50)),
                ("description", models.TextField()),
                ("resolved", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assessment_review", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="findings", to="assessment_review.assessmentreview")),
                ("question_review", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="findings", to="assessment_review.questionreview")),
            ],
            options={"db_table": "quality_finding", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ReviewDecision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("decision", models.CharField(choices=[("approved", "Approved"), ("needs_revision", "Needs Revision"), ("rejected", "Rejected"), ("archived", "Archived")], max_length=50)),
                ("rationale", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("decided_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assessment_review", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="decisions", to="assessment_review.assessmentreview")),
                ("decided_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assessment_review_decisions", to=settings.AUTH_USER_MODEL)),
                ("question_review", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="decisions", to="assessment_review.questionreview")),
            ],
            options={"db_table": "review_decision", "ordering": ["-decided_at"]},
        ),
        migrations.CreateModel(
            name="ReviewerAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("assigned", "Assigned"), ("reassigned", "Reassigned"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="assigned", max_length=50)),
                ("assigned_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assessment_review", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="assessment_review.assessmentreview")),
                ("question_review", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="assessment_review.questionreview")),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessment_review_assignments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "reviewer_assignment", "ordering": ["-assigned_at"]},
        ),
        migrations.AddIndex(model_name="assessmentreview", index=models.Index(fields=["assessment"], name="assess_review_assess_idx")),
        migrations.AddIndex(model_name="assessmentreview", index=models.Index(fields=["status"], name="assess_review_status_idx")),
        migrations.AddIndex(model_name="assessmentreview", index=models.Index(fields=["reviewer"], name="assess_review_reviewer_idx")),
        migrations.AddIndex(model_name="questionreview", index=models.Index(fields=["item_bank_entry"], name="question_review_item_idx")),
        migrations.AddIndex(model_name="questionreview", index=models.Index(fields=["status"], name="question_review_status_idx")),
        migrations.AddIndex(model_name="questionreview", index=models.Index(fields=["reviewer"], name="question_review_reviewer_idx")),
        migrations.AddIndex(model_name="reviewerassignment", index=models.Index(fields=["reviewer"], name="review_assign_reviewer_idx")),
        migrations.AddIndex(model_name="reviewerassignment", index=models.Index(fields=["status"], name="review_assign_status_idx")),
    ]
