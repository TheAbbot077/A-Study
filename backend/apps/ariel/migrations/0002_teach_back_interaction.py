# Generated for PI-8C.7 Ariel Teach-Back & Productive Struggle Engine
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("ariel", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArielTeachBackInteraction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("workspace_id", models.UUIDField(blank=True, null=True)),
                ("concept_reference", models.CharField(blank=True, max_length=255)),
                ("interaction_type", models.CharField(choices=[("restatement", "Restatement"), ("new_example", "New Example"), ("draw_or_diagram", "Draw Or Diagram"), ("label_diagram", "Label Diagram"), ("compare_cases", "Compare Cases"), ("what_if", "What If"), ("correct_ariel", "Correct Ariel"), ("reteach_after_delay", "Reteach After Delay"), ("unfamiliar_application", "Unfamiliar Application"), ("clarify_term", "Clarify Term"), ("explain_step", "Explain Step"), ("connect_ideas", "Connect Ideas"), ("resolve_contradiction", "Resolve Contradiction")], max_length=48)),
                ("status", models.CharField(choices=[("proposed", "Proposed"), ("active", "Active"), ("awaiting_learner", "Awaiting Learner"), ("awaiting_artefact", "Awaiting Artefact"), ("resolved", "Resolved"), ("skipped", "Skipped"), ("expired", "Expired"), ("cancelled", "Cancelled")], default="proposed", max_length=32)),
                ("strategy_reason_code", models.CharField(blank=True, max_length=64)),
                ("intensity", models.CharField(choices=[("light", "Light"), ("standard", "Standard"), ("deep", "Deep")], default="standard", max_length=16)),
                ("prompt_template_key", models.CharField(max_length=128)),
                ("prompt_template_version", models.CharField(default="1", max_length=32)),
                ("input_provenance", models.CharField(choices=[("direct_typed_explanation", "Direct Typed Explanation"), ("pasted_text", "Pasted Text"), ("imported_artefact", "Imported Artefact"), ("study_lab_artefact", "Study Lab Artefact"), ("voice_transcript", "Voice Transcript"), ("unknown", "Unknown")], default="unknown", max_length=48)),
                ("requires_artefact", models.BooleanField(default=False)),
                ("required_artefact_type", models.CharField(blank=True, max_length=64)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("presented_at", models.DateTimeField(blank=True, null=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("skipped_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("identity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teach_back_interactions", to="ariel.arielidentity")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_teach_back_interactions", to="users.user")),
                ("learning_journey", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ariel_teach_back_interactions", to="learning_journeys.learningjourney")),
                ("learner_response_turn", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="teach_back_interactions", to="ariel.arielteachingturn")),
                ("source_memory_unit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="teach_back_interactions", to="ariel.arielknowledgeunit")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ariel_teach_back_interactions", to="academic.subject")),
                ("teaching_session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teach_back_interactions", to="ariel.arielteachingsession")),
            ],
            options={
                "db_table": "ariel_teach_back_interaction",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="arielteachbackinteraction",
            index=models.Index(fields=["identity", "status"], name="ariel_tbi_identity_status_idx"),
        ),
        migrations.AddIndex(
            model_name="arielteachbackinteraction",
            index=models.Index(fields=["teaching_session", "status"], name="ariel_tbi_session_status_idx"),
        ),
        migrations.AddIndex(
            model_name="arielteachbackinteraction",
            index=models.Index(fields=["learner", "status"], name="ariel_tbi_learner_status_idx"),
        ),
        migrations.AddIndex(
            model_name="arielteachbackinteraction",
            index=models.Index(fields=["source_memory_unit"], name="ariel_tbi_source_memory_idx"),
        ),
        migrations.AddConstraint(
            model_name="arielteachbackinteraction",
            constraint=models.UniqueConstraint(
                fields=["teaching_session", "prompt_template_key", "version"],
                name="ariel_tbi_session_prompt_version_unique",
            ),
        ),
    ]
