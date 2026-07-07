import django.db.models.deletion
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0003_learning_resource"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentSection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("sequence_number", models.PositiveIntegerField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("learning_resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_sections", to="academic.learningresource")),
            ],
            options={
                "db_table": "academic_content_section",
                "ordering": ["sequence_number"],
            },
        ),
        migrations.AddConstraint(
            model_name="contentsection",
            constraint=models.UniqueConstraint(fields=("learning_resource", "sequence_number"), name="unique_learning_resource_sequence_number"),
        ),
        migrations.AddConstraint(
            model_name="contentsection",
            constraint=models.CheckConstraint(condition=models.Q(("sequence_number__gte", 1)), name="content_section_sequence_number_gte_1"),
        ),
        migrations.CreateModel(
            name="ContentConcept",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("learning_objective", models.TextField(blank=True)),
                ("sequence_number", models.PositiveIntegerField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("content_section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_concepts", to="academic.contentsection")),
            ],
            options={
                "db_table": "academic_content_concept",
                "ordering": ["sequence_number"],
            },
        ),
        migrations.AddConstraint(
            model_name="contentconcept",
            constraint=models.UniqueConstraint(fields=("content_section", "sequence_number"), name="unique_content_section_sequence_number"),
        ),
        migrations.AddConstraint(
            model_name="contentconcept",
            constraint=models.CheckConstraint(condition=models.Q(("sequence_number__gte", 1)), name="content_concept_sequence_number_gte_1"),
        ),
    ]
