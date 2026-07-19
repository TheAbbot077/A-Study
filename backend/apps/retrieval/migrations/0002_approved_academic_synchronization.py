import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0006_content_review_fields"),
        ("academic_review", "0003_controlled_academic_population"),
        ("retrieval", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RetrievalGeneration",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("building", "Building"), ("validating", "Validating"), ("active", "Active"), ("superseded", "Superseded"), ("failed", "Failed")], default="building", max_length=16)),
                ("source_fingerprint", models.CharField(max_length=128)),
                ("manifest_fingerprint", models.CharField(max_length=128)),
                ("chunk_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("promoted_at", models.DateTimeField(blank=True, null=True)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="retrieval_generations", to="academic.learningresource")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="retrieval_generations", to="academic.subject")),
            ],
            options={"db_table": "retrieval_generation"},
        ),
        migrations.AddConstraint(
            model_name="retrievalgeneration",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "active")), fields=("resource",), name="retrieval_one_active_generation"),
        ),
        migrations.AddIndex(
            model_name="retrievalgeneration",
            index=models.Index(fields=["resource", "status"], name="retrieval_gen_resource_status"),
        ),
        migrations.AlterField(
            model_name="retrievalchunk",
            name="collection",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="chunks", to="retrieval.retrievalchunkcollection"),
        ),
        migrations.AlterField(
            model_name="retrievalchunk",
            name="identity_key",
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name="retrievalchunk",
            name="population_job",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="retrieval_chunks", to="content_processing.academicpopulationjob"),
        ),
        migrations.AlterField(
            model_name="retrievalchunk",
            name="proposal",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="retrieval_chunks", to="content_processing.academicimportproposal"),
        ),
        migrations.AddField(
            model_name="retrievalchunk",
            name="generation",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="chunks", to="retrieval.retrievalgeneration"),
        ),
        migrations.AddConstraint(
            model_name="retrievalchunk",
            constraint=models.UniqueConstraint(fields=("generation", "identity_key"), name="retrieval_generation_chunk_key_unique"),
        ),
        migrations.AddConstraint(
            model_name="retrievalchunk",
            constraint=models.UniqueConstraint(fields=("generation", "ordering"), name="retrieval_generation_chunk_order_unique"),
        ),
        migrations.CreateModel(
            name="RetrievalSynchronizationRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("approved_projection_id", models.UUIDField()),
                ("processing_job_id", models.UUIDField(blank=True, null=True)),
                ("trigger", models.CharField(default="staff", max_length=32)),
                ("reason", models.TextField(blank=True)),
                ("idempotency_key", models.CharField(max_length=128, unique=True)),
                ("request_fingerprint", models.CharField(max_length=128)),
                ("source_fingerprint", models.CharField(max_length=128)),
                ("manifest_fingerprint", models.CharField(max_length=128)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("synchronizing", "Synchronizing"), ("synchronized", "Synchronized"), ("failed", "Failed")], default="planned", max_length=20)),
                ("planned_chunk_count", models.PositiveIntegerField(default=0)),
                ("indexed_chunk_count", models.PositiveIntegerField(default=0)),
                ("keyword_indexed_count", models.PositiveIntegerField(default=0)),
                ("vector_indexed_count", models.PositiveIntegerField(default=0)),
                ("failed_chunk_count", models.PositiveIntegerField(default=0)),
                ("citation_coverage", models.FloatField(default=0)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("failure_message", models.CharField(blank=True, max_length=500)),
                ("version", models.PositiveIntegerField(default=1)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("academic_population_run", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="retrieval_synchronization_runs", to="academic_review.academicpopulationrun")),
                ("prior_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="retries", to="retrieval.retrievalsynchronizationrun")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="retrieval_synchronization_runs", to=settings.AUTH_USER_MODEL)),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="retrieval_synchronization_runs", to="academic.learningresource")),
                ("retrieval_generation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="synchronization_runs", to="retrieval.retrievalgeneration")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="retrieval_synchronization_runs", to="academic.subject")),
            ],
            options={"db_table": "retrieval_synchronization_run"},
        ),
        migrations.AddIndex(model_name="retrievalsynchronizationrun", index=models.Index(fields=["academic_population_run", "status"], name="retrieval_sync_population")),
        migrations.AddIndex(model_name="retrievalsynchronizationrun", index=models.Index(fields=["resource", "status"], name="retrieval_sync_resource")),
        migrations.AddIndex(model_name="retrievalsynchronizationrun", index=models.Index(fields=["manifest_fingerprint", "status"], name="retrieval_sync_manifest")),
    ]
