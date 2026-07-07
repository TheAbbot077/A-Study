import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0004_learning_content"),
        ("storage", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResourceIngestionJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=50)),
                ("source_type", models.CharField(choices=[("manual", "Manual"), ("upload", "Upload"), ("import", "Import"), ("system", "System")], default="manual", max_length=50)),
                ("error_message", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("learning_resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ingestion_jobs", to="academic.learningresource")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ingestion_jobs", to="users.user")),
                ("stored_file", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ingestion_jobs", to="storage.storedfile")),
            ],
            options={
                "db_table": "academic_resource_ingestion_job",
                "ordering": ["-created_at"],
            },
        ),
    ]
