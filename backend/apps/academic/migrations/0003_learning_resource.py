import django.db.models.deletion
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0002_curriculum_models"),
        ("storage", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningResource",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("resource_type", models.CharField(choices=[("textbook", "Textbook"), ("notes", "Notes"), ("guide", "Guide"), ("reference", "Reference"), ("other", "Other")], default="other", max_length=50)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")], default="draft", max_length=50)),
                ("source_label", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("curriculum", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="learning_resources", to="academic.curriculum")),
                ("curriculum_unit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="learning_resources", to="academic.curriculumunit")),
                ("institution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="learning_resources", to="users.institution")),
                ("stored_file", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="learning_resources", to="storage.storedfile")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_resources", to="academic.subject")),
            ],
            options={
                "db_table": "academic_learning_resource",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="learningresource",
            index=models.Index(fields=["institution"], name="acad_lr_inst_idx"),
        ),
        migrations.AddIndex(
            model_name="learningresource",
            index=models.Index(fields=["subject"], name="acad_lr_subject_idx"),
        ),
        migrations.AddIndex(
            model_name="learningresource",
            index=models.Index(fields=["curriculum"], name="acad_lr_curr_idx"),
        ),
        migrations.AddIndex(
            model_name="learningresource",
            index=models.Index(fields=["curriculum_unit"], name="acad_lr_unit_idx"),
        ),
        migrations.AddIndex(
            model_name="learningresource",
            index=models.Index(fields=["resource_type"], name="acad_lr_type_idx"),
        ),
        migrations.AddIndex(
            model_name="learningresource",
            index=models.Index(fields=["status"], name="acad_lr_status_idx"),
        ),
    ]
