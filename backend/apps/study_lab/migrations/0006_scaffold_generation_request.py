import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("study_lab", "0005_instrument_suite_catalog"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudyScaffoldGenerationRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("generation_type", models.CharField(choices=[("EQUATION_AND_FORMULA_SHEET", "Equation and formula sheet"), ("DIAGRAM_AND_CONCEPT_MAP", "Diagram and concept map"), ("FLASHCARDS_AND_SCRATCHPAD", "Flashcards and scratchpad"), ("CODE_ARTIFACT", "Code artefact")], max_length=48)),
                ("requested_artefact_type", models.CharField(choices=[("TEXT_NOTE", "Text note"), ("FLASHCARD_SET", "Flashcard set"), ("FLASHCARD", "Flashcard"), ("FORMULA_SHEET", "Formula sheet"), ("EQUATION_ARTEFACT", "Equation artefact"), ("GRAPH_ARTEFACT", "Graph artefact"), ("REVISION_SUMMARY", "Revision summary"), ("WHITEBOARD_SNAPSHOT", "Whiteboard snapshot"), ("RESOURCE_EXCERPT", "Resource excerpt"), ("SESSION_SUMMARY", "Session summary"), ("LESSON_REFERENCE", "Lesson reference"), ("CONCEPT_REFERENCE", "Concept reference"), ("CONCEPT_MAP", "Concept map"), ("FLOWCHART", "Flowchart"), ("TIMELINE", "Timeline"), ("COMPARISON_TABLE", "Comparison table"), ("DIAGRAM_ARTEFACT", "Diagram artefact"), ("LEARNER_EXPLANATION", "Learner explanation"), ("ARIEL_TEACHING_ARTEFACT", "Ariel teaching artefact"), ("ABBOT_LESSON_REFERENCE", "Abbot lesson reference"), ("CONCEPT_CHECK_RECEIPT", "Concept check receipt"), ("SCRATCHPAD_ARTEFACT", "Scratchpad artefact"), ("NOTE_CARD_SET", "Note card set"), ("DATA_TABLE", "Data table"), ("CODE_ARTEFACT", "Code artefact")], max_length=48)),
                ("provider_context", models.CharField(choices=[("ABBOT", "Abbot"), ("ARIEL", "Ariel"), ("WHITEBOARD", "Whiteboard"), ("RESOURCE", "Resource"), ("CONCEPT_CHECK", "Concept Check"), ("PROGRESS", "Progress"), ("JOURNEY", "Journey"), ("STUDY_LAB", "Study Lab")], default="STUDY_LAB", max_length=32)),
                ("provider_reference", models.CharField(blank=True, max_length=128)),
                ("policy_version", models.CharField(default="1", max_length=32)),
                ("idempotency_key", models.CharField(blank=True, max_length=128)),
                ("request_checksum", models.CharField(blank=True, max_length=128)),
                ("status", models.CharField(choices=[("REQUESTED", "Requested"), ("VALIDATING", "Validating"), ("READY", "Ready"), ("PROCESSING", "Processing"), ("COMPLETED", "Completed"), ("FAILED", "Failed"), ("CANCELLED", "Cancelled")], default="REQUESTED", max_length=24)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("failure_detail", models.CharField(blank=True, max_length=280)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("validating_at", models.DateTimeField(blank=True, null=True)),
                ("ready_at", models.DateTimeField(blank=True, null=True)),
                ("processing_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="study_lab_scaffold_generation_requests", to=settings.AUTH_USER_MODEL)),
                ("result_artefact", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="generated_from_requests", to="study_lab.studyartefact")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scaffold_generation_requests", to="study_lab.studyworkspace")),
            ],
            options={
                "db_table": "study_lab_scaffold_generation_request",
                "ordering": ["-requested_at"],
            },
        ),
        migrations.AddField(
            model_name="studyscaffoldgenerationrequest",
            name="source_artefacts",
            field=models.ManyToManyField(blank=True, related_name="scaffold_generation_sources", to="study_lab.studyartefact"),
        ),
        migrations.AddIndex(
            model_name="studyscaffoldgenerationrequest",
            index=models.Index(fields=["workspace", "status"], name="sl_sgr_ws_status_idx"),
        ),
        migrations.AddIndex(
            model_name="studyscaffoldgenerationrequest",
            index=models.Index(fields=["learner", "status"], name="sl_sgr_learner_status_idx"),
        ),
        migrations.AddIndex(
            model_name="studyscaffoldgenerationrequest",
            index=models.Index(fields=["idempotency_key"], name="sl_sgr_idem_idx"),
        ),
        migrations.AddConstraint(
            model_name="studyscaffoldgenerationrequest",
            constraint=models.UniqueConstraint(condition=~Q(idempotency_key=""), fields=("workspace", "generation_type", "idempotency_key"), name="sl_sgr_unique_ws_type_idem"),
        ),
    ]
