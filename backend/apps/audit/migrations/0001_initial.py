from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0004_alter_institution_institution_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=255)),
                ("target_type", models.CharField(blank=True, max_length=255)),
                ("target_id", models.CharField(blank=True, max_length=255)),
                ("target_display", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_entries", to="users.user")),
                ("institution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_entries", to="users.institution")),
            ],
            options={
                "db_table": "audit_audit_entry",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["actor"], name="audit_actor_idx"),
                    models.Index(fields=["institution"], name="audit_inst_idx"),
                    models.Index(fields=["action"], name="audit_action_idx"),
                    models.Index(fields=["target_type", "target_id"], name="audit_target_idx"),
                    models.Index(fields=["created_at"], name="audit_created_idx"),
                ],
            },
        ),
    ]
