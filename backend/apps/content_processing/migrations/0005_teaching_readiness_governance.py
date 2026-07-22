import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0006_content_review_fields"),
        ("content_processing", "0004_academic_proposals_and_population"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TeachingReadinessEvaluation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("processing_attempt_id", models.UUIDField(blank=True, null=True)),
                ("approved_projection_id", models.UUIDField(blank=True, null=True)),
                ("approval_decision_id", models.UUIDField(blank=True, null=True)),
                ("academic_population_run_id", models.UUIDField(blank=True, null=True)),
                ("retrieval_synchronization_run_id", models.UUIDField(blank=True, null=True)),
                ("retrieval_generation_id", models.UUIDField(blank=True, null=True)),
                ("trigger", models.CharField(default="staff", max_length=32)),
                ("reason", models.TextField(blank=True)),
                ("idempotency_key", models.CharField(max_length=128, unique=True)),
                ("request_fingerprint", models.CharField(max_length=128)),
                ("lineage_fingerprint", models.CharField(max_length=128)),
                ("policy_version", models.CharField(max_length=64)),
                ("decision", models.CharField(choices=[("ready", "Ready"), ("blocked", "Blocked"), ("stale", "Stale")], max_length=16)),
                ("checks_passed", models.PositiveIntegerField(default=0)),
                ("checks_failed", models.PositiveIntegerField(default=0)),
                ("blocker_count", models.PositiveIntegerField(default=0)),
                ("warning_count", models.PositiveIntegerField(default=0)),
                ("snapshot", models.JSONField(default=dict)),
                ("checks", models.JSONField(default=list)),
                ("invalidated_at", models.DateTimeField(blank=True, null=True)),
                ("invalidation_reason", models.CharField(blank=True, max_length=128)),
                ("evaluated_at", models.DateTimeField(auto_now_add=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processing_job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teaching_readiness_evaluations", to="content_processing.contentprocessingjob")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="teaching_readiness_evaluations", to=settings.AUTH_USER_MODEL)),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teaching_readiness_evaluations", to="academic.learningresource")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teaching_readiness_evaluations", to="academic.subject")),
                ("supersedes_evaluation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="superseded_by", to="content_processing.teachingreadinessevaluation")),
            ],
            options={"db_table": "content_processing_teaching_readiness_evaluation", "ordering": ["-evaluated_at"]},
        ),
        migrations.AddConstraint(
            model_name="teachingreadinessevaluation",
            constraint=models.UniqueConstraint(fields=("resource", "lineage_fingerprint", "policy_version"), name="cp_readiness_lineage_policy_unique"),
        ),
        migrations.AddIndex(model_name="teachingreadinessevaluation", index=models.Index(fields=["resource", "decision"], name="cp_ready_resource_decision")),
        migrations.AddIndex(model_name="teachingreadinessevaluation", index=models.Index(fields=["processing_job", "evaluated_at"], name="cp_ready_job_evaluated")),
        migrations.AddIndex(model_name="teachingreadinessevaluation", index=models.Index(fields=["lineage_fingerprint"], name="cp_ready_lineage")),
    ]
