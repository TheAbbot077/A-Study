from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("study_lab", "0003_tool_session_commands"),
    ]

    operations = [
        migrations.AddField(
            model_name="studytooldefinition",
            name="instrument_family",
            field=models.CharField(default="GENERAL_THINKING", choices=[("COMPUTATIONAL", "Computational"), ("GRAPHING", "Graphing"), ("MATHEMATICAL_CONSTRUCTION", "Mathematical construction"), ("VISUAL_REASONING", "Visual reasoning"), ("MEMORY_AND_REVIEW", "Memory and review"), ("GENERAL_THINKING", "General thinking"), ("TECHNICAL", "Technical")], max_length=48),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="input_artefact_types",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="output_artefact_types",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="schema_versions",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="supports_transform",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="supports_import",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="supports_export",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="requires_runtime",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="runtime_provider",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="studytooldefinition",
            name="offline_capable",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="studytoolmanifest",
            name="supported_schema_versions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
