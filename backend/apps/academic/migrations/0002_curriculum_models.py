import django.db.models.deletion
import django.db.models.expressions
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Curriculum",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("version", models.CharField(default="1.0", max_length=50)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("institution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="curricula", to="users.institution")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="curricula", to="academic.subject")),
            ],
            options={
                "db_table": "academic_curriculum",
                "ordering": ["subject", "name", "version"],
            },
        ),
        migrations.AddConstraint(
            model_name="curriculum",
            constraint=models.UniqueConstraint(fields=("subject", "institution", "version"), name="unique_subject_institution_version"),
        ),
        migrations.CreateModel(
            name="CurriculumUnit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("sequence_number", models.PositiveIntegerField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("curriculum", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="units", to="academic.curriculum")),
            ],
            options={
                "db_table": "academic_curriculum_unit",
                "ordering": ["sequence_number"],
            },
        ),
        migrations.AddConstraint(
            model_name="curriculumunit",
            constraint=models.UniqueConstraint(fields=("curriculum", "sequence_number"), name="unique_curriculum_sequence_number"),
        ),
        migrations.AddConstraint(
            model_name="curriculumunit",
            constraint=models.CheckConstraint(condition=models.Q(("sequence_number__gte", 1)), name="curriculum_unit_sequence_number_gte_1"),
        ),
    ]
