import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("academic", "0006_content_review_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentImportJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("format_type", models.CharField(choices=[("pdf", "PDF"), ("docx", "DOCX")], max_length=20)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("error_message", models.TextField(blank=True)),
                ("ocr_requested", models.BooleanField(default=False)),
                ("ocr_used", models.BooleanField(default=False)),
                ("extraction_confidence", models.FloatField(blank=True, null=True)),
                ("section_confidence", models.FloatField(blank=True, null=True)),
                ("concept_confidence", models.FloatField(blank=True, null=True)),
                ("structural_confidence", models.FloatField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("learning_resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_import_jobs", to="academic.learningresource")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_import_jobs", to=settings.AUTH_USER_MODEL)),
                ("stored_file", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_import_jobs", to="storage.storedfile")),
            ],
            options={"db_table": "content_intelligence_import_job", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ContentValidationFinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="medium", max_length=20)),
                ("finding_type", models.CharField(max_length=100)),
                ("message", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("import_job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="validation_findings", to="content_intelligence.contentimportjob")),
            ],
            options={"db_table": "content_intelligence_validation_finding", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ParsedDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("normalized_text", models.TextField(blank=True)),
                ("format_type", models.CharField(choices=[("pdf", "PDF"), ("docx", "DOCX")], max_length=20)),
                ("extraction_method", models.CharField(max_length=100)),
                ("page_count", models.PositiveIntegerField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("import_job", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="parsed_document", to="content_intelligence.contentimportjob")),
            ],
            options={"db_table": "content_intelligence_parsed_document", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ContentExtractionResult",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("extracted_text", models.TextField(blank=True)),
                ("normalized_text", models.TextField(blank=True)),
                ("extraction_method", models.CharField(max_length=100)),
                ("sufficient_text", models.BooleanField(default=False)),
                ("ocr_requested", models.BooleanField(default=False)),
                ("ocr_used", models.BooleanField(default=False)),
                ("char_count", models.PositiveIntegerField(default=0)),
                ("page_count", models.PositiveIntegerField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("import_job", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="extraction_result", to="content_intelligence.contentimportjob")),
            ],
            options={"db_table": "content_intelligence_extraction_result", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ParserPipelineRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="pending", max_length=20)),
                ("current_stage", models.CharField(blank=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("import_job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pipeline_runs", to="content_intelligence.contentimportjob")),
            ],
            options={"db_table": "content_intelligence_pipeline_run", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ParsedSection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("heading", models.CharField(max_length=255)),
                ("body_text", models.TextField(blank=True)),
                ("sequence_number", models.PositiveIntegerField()),
                ("section_type", models.CharField(choices=[("front_matter", "Front Matter"), ("chapter", "Chapter"), ("appendix", "Appendix"), ("unknown", "Unknown")], default="unknown", max_length=30)),
                ("confidence", models.FloatField(default=0.0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("parsed_document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="content_intelligence.parseddocument")),
            ],
            options={"db_table": "content_intelligence_parsed_section", "ordering": ["sequence_number"]},
        ),
        migrations.CreateModel(
            name="ParsedConceptCandidate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("learning_objective", models.TextField(blank=True)),
                ("sequence_number", models.PositiveIntegerField()),
                ("confidence", models.FloatField(default=0.0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("parsed_section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concept_candidates", to="content_intelligence.parsedsection")),
            ],
            options={"db_table": "content_intelligence_concept_candidate", "ordering": ["sequence_number"]},
        ),
        migrations.AddIndex(model_name="contentimportjob", index=models.Index(fields=["learning_resource"], name="ci_job_resource_idx")),
        migrations.AddIndex(model_name="contentimportjob", index=models.Index(fields=["status"], name="ci_job_status_idx")),
        migrations.AddIndex(model_name="contentimportjob", index=models.Index(fields=["format_type"], name="ci_job_format_idx")),
        migrations.AddConstraint(model_name="parsedsection", constraint=models.UniqueConstraint(fields=("parsed_document", "sequence_number"), name="unique_ci_parsed_section_sequence")),
        migrations.AddConstraint(model_name="parsedsection", constraint=models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="ci_parsed_section_sequence_gte_1")),
        migrations.AddConstraint(model_name="parsedconceptcandidate", constraint=models.UniqueConstraint(fields=("parsed_section", "sequence_number"), name="unique_ci_concept_candidate_sequence")),
        migrations.AddConstraint(model_name="parsedconceptcandidate", constraint=models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="ci_concept_candidate_sequence_gte_1")),
    ]
