import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("academic", "0006_content_review_fields"),
        ("content_intelligence", "0001_initial"),
        ("storage", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentProcessingJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("pipeline_version", models.CharField(default="content-processing-v1", max_length=100)),
                ("status", models.CharField(choices=[("active", "Active"), ("ready_for_review", "Ready For Review"), ("ready_for_teaching", "Ready For Teaching"), ("failed", "Failed"), ("cancelled", "Cancelled"), ("deleted", "Deleted")], default="active", max_length=50)),
                ("current_stage", models.CharField(choices=[("created", "Created"), ("queued", "Queued"), ("inspecting", "Inspecting"), ("extracting", "Extracting"), ("structuring", "Structuring"), ("segmenting", "Segmenting"), ("validating", "Validating"), ("populating", "Populating"), ("indexing", "Indexing")], default="created", max_length=50)),
                ("progress", models.PositiveIntegerField(default=0)),
                ("active_attempt_number", models.PositiveIntegerField(default=0)),
                ("cancellation_requested", models.BooleanField(default=False)),
                ("failure", models.JSONField(blank=True, default=dict)),
                ("queued_at", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("last_transition_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("transition_version", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("legacy_import_job", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="processing_job", to="content_intelligence.contentimportjob")),
                ("resource", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_processing_jobs", to="academic.learningresource")),
                ("stored_file", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_processing_jobs", to="storage.storedfile")),
            ],
            options={
                "db_table": "content_processing_job",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ProcessingAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("attempt_number", models.PositiveIntegerField()),
                ("trigger", models.CharField(choices=[("initial_upload", "Initial Upload"), ("automatic_retry", "Automatic Retry"), ("manual_retry", "Manual Retry"), ("full_reprocess", "Full Reprocess"), ("admin_reprocess", "Admin Reprocess")], max_length=50)),
                ("restart_stage", models.CharField(choices=[("created", "Created"), ("queued", "Queued"), ("inspecting", "Inspecting"), ("extracting", "Extracting"), ("structuring", "Structuring"), ("segmenting", "Segmenting"), ("validating", "Validating"), ("populating", "Populating"), ("indexing", "Indexing")], default="inspecting", max_length=50)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=50)),
                ("failure", models.JSONField(blank=True, default=dict)),
                ("correlation_id", models.CharField(blank=True, max_length=255)),
                ("task_id", models.CharField(blank=True, max_length=255)),
                ("diagnostic_summary", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("initiated_by_actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_processing_attempts", to=settings.AUTH_USER_MODEL)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="content_processing.contentprocessingjob")),
            ],
            options={
                "db_table": "content_processing_attempt",
                "ordering": ["-attempt_number"],
            },
        ),
        migrations.CreateModel(
            name="ProcessingDiagnostic",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("stage", models.CharField(choices=[("created", "Created"), ("queued", "Queued"), ("inspecting", "Inspecting"), ("extracting", "Extracting"), ("structuring", "Structuring"), ("segmenting", "Segmenting"), ("validating", "Validating"), ("populating", "Populating"), ("indexing", "Indexing")], max_length=50)),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error"), ("fatal", "Fatal")], max_length=20)),
                ("code", models.CharField(max_length=100)),
                ("public_message", models.TextField()),
                ("internal_message", models.TextField(blank=True)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("source_component", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="diagnostics", to="content_processing.processingattempt")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="diagnostics", to="content_processing.contentprocessingjob")),
            ],
            options={
                "db_table": "content_processing_diagnostic",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="ProcessingStageResult",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("stage", models.CharField(choices=[("created", "Created"), ("queued", "Queued"), ("inspecting", "Inspecting"), ("extracting", "Extracting"), ("structuring", "Structuring"), ("segmenting", "Segmenting"), ("validating", "Validating"), ("populating", "Populating"), ("indexing", "Indexing")], max_length=50)),
                ("pipeline_version", models.CharField(max_length=100)),
                ("result_version", models.PositiveIntegerField(default=1)),
                ("idempotency_key", models.CharField(max_length=255)),
                ("output_references", models.JSONField(blank=True, default=dict)),
                ("checksum", models.CharField(blank=True, max_length=255)),
                ("completed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stage_results", to="content_processing.processingattempt")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stage_results", to="content_processing.contentprocessingjob")),
            ],
            options={
                "db_table": "content_processing_stage_result",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="contentprocessingjob",
            constraint=models.CheckConstraint(condition=models.Q(progress__gte=0) & models.Q(progress__lte=100), name="cp_job_progress_range"),
        ),
        migrations.AddConstraint(
            model_name="contentprocessingjob",
            constraint=models.UniqueConstraint(
                fields=("resource", "stored_file", "pipeline_version"),
                condition=~models.Q(status="deleted"),
                name="cp_job_active_identity_unique",
            ),
        ),
        migrations.AddIndex(model_name="contentprocessingjob", index=models.Index(fields=["status"], name="cp_job_status_idx")),
        migrations.AddIndex(model_name="contentprocessingjob", index=models.Index(fields=["current_stage"], name="cp_job_stage_idx")),
        migrations.AddIndex(model_name="contentprocessingjob", index=models.Index(fields=["resource"], name="cp_job_resource_idx")),
        migrations.AddIndex(model_name="contentprocessingjob", index=models.Index(fields=["stored_file"], name="cp_job_file_idx")),
        migrations.AddIndex(model_name="contentprocessingjob", index=models.Index(fields=["pipeline_version"], name="cp_job_pipeline_idx")),
        migrations.AddConstraint(
            model_name="processingattempt",
            constraint=models.UniqueConstraint(fields=("job", "attempt_number"), name="cp_attempt_number_unique"),
        ),
        migrations.AddIndex(model_name="processingdiagnostic", index=models.Index(fields=["job", "severity"], name="cp_diag_job_severity_idx")),
        migrations.AddIndex(model_name="processingdiagnostic", index=models.Index(fields=["attempt"], name="cp_diag_attempt_idx")),
        migrations.AddConstraint(
            model_name="processingstageresult",
            constraint=models.UniqueConstraint(fields=("job", "attempt", "stage", "result_version"), name="cp_stage_result_unique"),
        ),
    ]
