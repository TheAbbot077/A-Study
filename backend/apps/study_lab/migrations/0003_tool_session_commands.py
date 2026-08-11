from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("study_lab", "0002_tool_platform_artefacts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workspacetoolinvocation",
            name="status",
            field=models.CharField(choices=[("REQUESTED", "Requested"), ("VALIDATED", "Validated"), ("DISPATCHED", "Dispatched"), ("RUNNING", "Running"), ("COMPLETED", "Completed"), ("FAILED", "Failed"), ("CANCELLED", "Cancelled")], default="REQUESTED", max_length=24),
        ),
        migrations.CreateModel(
            name="WorkspaceToolSessionCommand",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("operation", models.CharField(max_length=24)),
                ("idempotency_key", models.CharField(blank=True, max_length=128)),
                ("status", models.CharField(default="REQUESTED", max_length=24)),
                ("provider_reference", models.CharField(blank=True, max_length=128)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("reason_code", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="study_lab_tool_session_commands", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="commands", to="study_lab.workspacetoolsession")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tool_session_commands", to="study_lab.studyworkspace")),
            ],
            options={
                "db_table": "study_lab_tool_session_command",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="workspacetoolsessioncommand",
            constraint=models.UniqueConstraint(condition=~Q(idempotency_key=""), fields=("session", "operation", "idempotency_key"), name="sl_tsc_unique_session_op_idem"),
        ),
    ]
