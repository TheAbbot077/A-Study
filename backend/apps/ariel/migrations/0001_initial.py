# Generated for PI-8C.2 Ariel Constitution & Learner-Taught Memory Platform
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("users", "0003_institution_institutionmembership"),
        ("academic", "0006_content_review_fields"),
        ("learning_journeys", "0005_operational_workflows"),
    ]

    operations = [
        # Constitution
        migrations.CreateModel(
            name="ArielConstitution",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("version", models.CharField(max_length=32, unique=True)),
                ("rules", models.JSONField(blank=True, default=list)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ariel_constitution", "ordering": ["-created_at"]},
        ),
        # Identity
        migrations.CreateModel(
            name="ArielIdentity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "active"), ("suspended", "Suspended"), ("archived", "Archived")], default="draft", max_length=24)),
                ("display_name", models.CharField(default="Ariel", max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("suspended_at", models.DateTimeField(blank=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("constitution", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_identities", to="ariel.arielconstitution")),
                ("institution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ariel_identities", to="users.institution")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_identities", to="users.user")),
            ],
            options={"db_table": "ariel_identity"},
        ),
        # Relationship
        migrations.CreateModel(
            name="ArielRelationship",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("consent_state", models.CharField(choices=[("pending", "Pending"), ("granted", "Granted"), ("withdrawn", "Withdrawn")], default="pending", max_length=24)),
                ("institutional_visibility", models.CharField(choices=[("private", "Private"), ("metadata_only", "Metadata Only"), ("aggregate", "Aggregate")], default="private", max_length=24)),
                ("status", models.CharField(choices=[("active", "Active"), ("suspended", "Suspended"), ("terminated", "Terminated")], default="active", max_length=24)),
                ("privacy_policy", models.JSONField(blank=True, default=dict)),
                ("retention_policy", models.JSONField(blank=True, default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("consent_granted_at", models.DateTimeField(blank=True, null=True)),
                ("consent_withdrawn_at", models.DateTimeField(blank=True, null=True)),
                ("identity", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="relationship", to="ariel.arielidentity")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_relationships", to="users.user")),
            ],
            options={"db_table": "ariel_relationship"},
        ),
        # Teaching Session
        migrations.CreateModel(
            name="ArielTeachingSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("concept_reference", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("active", "Active"), ("completed", "Completed"), ("abandoned", "Abandoned")], default="active", max_length=24)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("constitution", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teaching_sessions", to="ariel.arielconstitution")),
                ("identity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teaching_sessions", to="ariel.arielidentity")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_teaching_sessions", to="users.user")),
                ("learning_journey", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ariel_teaching_sessions", to="learning_journeys.learningjourney")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ariel_teaching_sessions", to="academic.subject")),
            ],
            options={"db_table": "ariel_teaching_session"},
        ),
        # Teaching Turn
        migrations.CreateModel(
            name="ArielTeachingTurn",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("actor", models.CharField(choices=[("learner", "Learner"), ("ariel", "Ariel")], max_length=16)),
                ("content", models.TextField()),
                ("sequence_number", models.PositiveIntegerField()),
                ("disposition", models.CharField(choices=[("conversation", "Conversation"), ("teaching", "Teaching"), ("correction", "Correction"), ("reinforcement", "Reinforcement"), ("forgetting", "Forgetting"), ("inspection", "Inspection"), ("question", "Question")], default="conversation", max_length=24)),
                ("provenance", models.CharField(blank=True, choices=[("learner_teaching", "Learner Teaching"), ("learner_correction", "Learner Correction"), ("learner_reinforcement", "Learner Reinforcement")], max_length=48)),
                ("resulting_memory_effect", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="turns", to="ariel.arielteachingsession")),
            ],
            options={"db_table": "ariel_teaching_turn", "ordering": ["session_id", "sequence_number"]},
        ),
        # Knowledge Unit
        migrations.CreateModel(
            name="ArielKnowledgeUnit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("normalized_statement", models.TextField()),
                ("confidence", models.DecimalField(decimal_places=3, default=0.5, max_digits=4)),
                ("memory_state", models.CharField(choices=[("new", "New"), ("fragile", "Fragile"), ("reinforced", "Reinforced"), ("stable", "Stable"), ("conflicted", "Conflicted"), ("misconceived", "Misconceived"), ("forgotten", "Forgotten"), ("superseded", "Superseded"), ("retracted", "Retracted")], default="new", max_length=24)),
                ("provenance", models.CharField(choices=[("learner_teaching", "Learner Teaching"), ("learner_correction", "Learner Correction"), ("learner_reinforcement", "Learner Reinforcement")], default="learner_teaching", max_length=48)),
                ("concept_reference", models.CharField(blank=True, max_length=255)),
                ("forgetting_metadata", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
                ("forgotten_at", models.DateTimeField(blank=True, null=True)),
                ("retracted_at", models.DateTimeField(blank=True, null=True)),
                ("identity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="knowledge_units", to="ariel.arielidentity")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_knowledge_units", to="users.user")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="knowledge_units", to="ariel.arielteachingsession")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ariel_knowledge_units", to="academic.subject")),
                ("superseded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="supersedes", to="ariel.arielknowledgeunit")),
                ("teaching_turn", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="knowledge_units", to="ariel.arielteachingturn")),
            ],
            options={"db_table": "ariel_knowledge_unit"},
        ),
        # Memory Record
        migrations.CreateModel(
            name="ArielMemoryRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("previous_state", models.CharField(choices=[("new", "New"), ("fragile", "Fragile"), ("reinforced", "Reinforced"), ("stable", "Stable"), ("conflicted", "Conflicted"), ("misconceived", "Misconceived"), ("forgotten", "Forgotten"), ("superseded", "Superseded"), ("retracted", "Retracted")], max_length=24)),
                ("new_state", models.CharField(choices=[("new", "New"), ("fragile", "Fragile"), ("reinforced", "Reinforced"), ("stable", "Stable"), ("conflicted", "Conflicted"), ("misconceived", "Misconceived"), ("forgotten", "Forgotten"), ("superseded", "Superseded"), ("retracted", "Retracted")], max_length=24)),
                ("previous_confidence", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ("new_confidence", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ("transition_reason", models.CharField(blank=True, max_length=64)),
                ("provenance", models.CharField(choices=[("learner_teaching", "Learner Teaching"), ("learner_correction", "Learner Correction"), ("learner_reinforcement", "Learner Reinforcement")], max_length=48)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("identity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memory_records", to="ariel.arielidentity")),
                ("knowledge_unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memory_records", to="ariel.arielknowledgeunit")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_memory_records", to="users.user")),
            ],
            options={"db_table": "ariel_memory_record", "ordering": ["-created_at"]},
        ),
        # Misconception
        migrations.CreateModel(
            name="ArielMisconception",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("original_explanation", models.TextField()),
                ("resulting_belief", models.TextField()),
                ("contradiction_history", models.JSONField(blank=True, default=list)),
                ("correction_history", models.JSONField(blank=True, default=list)),
                ("current_state", models.CharField(choices=[("new", "New"), ("fragile", "Fragile"), ("reinforced", "Reinforced"), ("stable", "Stable"), ("conflicted", "Conflicted"), ("misconceived", "Misconceived"), ("forgotten", "Forgotten"), ("superseded", "Superseded"), ("retracted", "Retracted")], default="misconceived", max_length=24)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("identity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="misconceptions", to="ariel.arielidentity")),
                ("knowledge_unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="misconceptions", to="ariel.arielknowledgeunit")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_misconceptions", to="users.user")),
            ],
            options={"db_table": "ariel_misconception"},
        ),
        # Correction Record
        migrations.CreateModel(
            name="ArielCorrectionRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("correction_reason", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("identity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="correction_records", to="ariel.arielidentity")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_correction_records", to="users.user")),
                ("replacement_knowledge", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="corrections_replacing", to="ariel.arielknowledgeunit")),
                ("superseded_knowledge", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="corrections_superseding", to="ariel.arielknowledgeunit")),
                ("teaching_turn", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="correction_records", to="ariel.arielteachingturn")),
            ],
            options={"db_table": "ariel_correction_record"},
        ),
        # Reinforcement Record
        migrations.CreateModel(
            name="ArielReinforcementRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("previous_confidence", models.DecimalField(decimal_places=3, max_digits=4)),
                ("updated_confidence", models.DecimalField(decimal_places=3, max_digits=4)),
                ("previous_state", models.CharField(choices=[("new", "New"), ("fragile", "Fragile"), ("reinforced", "Reinforced"), ("stable", "Stable"), ("conflicted", "Conflicted"), ("misconceived", "Misconceived"), ("forgotten", "Forgotten"), ("superseded", "Superseded"), ("retracted", "Retracted")], max_length=24)),
                ("new_state", models.CharField(choices=[("new", "New"), ("fragile", "Fragile"), ("reinforced", "Reinforced"), ("stable", "Stable"), ("conflicted", "Conflicted"), ("misconceived", "Misconceived"), ("forgotten", "Forgotten"), ("superseded", "Superseded"), ("retracted", "Retracted")], max_length=24)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("identity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reinforcement_records", to="ariel.arielidentity")),
                ("knowledge_unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reinforcement_records", to="ariel.arielknowledgeunit")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_reinforcement_records", to="users.user")),
                ("teaching_turn", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reinforcement_records", to="ariel.arielteachingturn")),
            ],
            options={"db_table": "ariel_reinforcement_record", "ordering": ["-created_at"]},
        ),
        # User Capability
        migrations.CreateModel(
            name="ArielUserCapability",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("capability_code", models.CharField(choices=[("ariel.use", "Ariel Use"), ("ariel.view_memory", "Ariel View Memory"), ("ariel.correct_memory", "Ariel Correct Memory"), ("ariel.forget_memory", "Ariel Forget Memory"), ("ariel.reset", "Ariel Reset"), ("ariel.export", "Ariel Export"), ("ariel.suspend", "Ariel Suspend"), ("ariel.admin_status", "Ariel Admin Status"), ("ariel.admin_suspend", "Ariel Admin Suspend"), ("ariel.admin_restore", "Ariel Admin Restore"), ("ariel.admin_view_audit", "Ariel Admin View Audit")], max_length=64)),
                ("granted_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("granted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="granted_ariel_capabilities", to="users.user")),
                ("identity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_capabilities", to="ariel.arielidentity")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ariel_capabilities", to="users.user")),
            ],
            options={"db_table": "ariel_user_capability"},
        ),
        # Indexes
        migrations.AddIndex(model_name="arielidentity", index=models.Index(fields=["learner", "status"], name="ariel_id_learner_status_idx")),
        migrations.AddIndex(model_name="arielidentity", index=models.Index(fields=["institution", "status"], name="ariel_id_inst_status_idx")),
        migrations.AddIndex(model_name="arielrelationship", index=models.Index(fields=["learner", "status"], name="ariel_rel_learner_status_idx")),
        migrations.AddIndex(model_name="arielteachingsession", index=models.Index(fields=["identity", "status"], name="ariel_ts_identity_status_idx")),
        migrations.AddIndex(model_name="arielteachingsession", index=models.Index(fields=["learner", "status"], name="ariel_ts_learner_status_idx")),
        migrations.AddIndex(model_name="arielteachingsession", index=models.Index(fields=["learning_journey"], name="ariel_ts_journey_idx")),
        migrations.AddIndex(model_name="arielteachingturn", index=models.Index(fields=["session", "sequence_number"], name="ariel_tt_session_seq_idx")),
        migrations.AddIndex(model_name="arielteachingturn", index=models.Index(fields=["actor", "disposition"], name="ariel_tt_actor_disp_idx")),
        migrations.AddIndex(model_name="arielknowledgeunit", index=models.Index(fields=["identity", "memory_state"], name="ariel_ku_identity_state_idx")),
        migrations.AddIndex(model_name="arielknowledgeunit", index=models.Index(fields=["learner", "memory_state"], name="ariel_ku_learner_state_idx")),
        migrations.AddIndex(model_name="arielknowledgeunit", index=models.Index(fields=["subject"], name="ariel_ku_subject_idx")),
        migrations.AddIndex(model_name="arielknowledgeunit", index=models.Index(fields=["provenance"], name="ariel_ku_provenance_idx")),
        migrations.AddIndex(model_name="arielmemoryrecord", index=models.Index(fields=["identity", "created_at"], name="ariel_mr_identity_time_idx")),
        migrations.AddIndex(model_name="arielmemoryrecord", index=models.Index(fields=["knowledge_unit", "created_at"], name="ariel_mr_ku_time_idx")),
        migrations.AddIndex(model_name="arielmemoryrecord", index=models.Index(fields=["learner", "created_at"], name="ariel_mr_learner_time_idx")),
        migrations.AddIndex(model_name="arielmisconception", index=models.Index(fields=["identity", "current_state"], name="ariel_mc_identity_state_idx")),
        migrations.AddIndex(model_name="arielmisconception", index=models.Index(fields=["knowledge_unit"], name="ariel_mc_ku_idx")),
        migrations.AddIndex(model_name="arielcorrectionrecord", index=models.Index(fields=["identity", "created_at"], name="ariel_cr_identity_time_idx")),
        migrations.AddIndex(model_name="arielcorrectionrecord", index=models.Index(fields=["superseded_knowledge"], name="ariel_cr_superseded_idx")),
        migrations.AddIndex(model_name="arielreinforcementrecord", index=models.Index(fields=["knowledge_unit", "created_at"], name="ariel_rr_ku_time_idx")),
        migrations.AddIndex(model_name="arielreinforcementrecord", index=models.Index(fields=["identity", "created_at"], name="ariel_rr_identity_time_idx")),
        migrations.AddIndex(model_name="arielusercapability", index=models.Index(fields=["user", "capability_code"], name="ariel_uc_user_cap_idx")),
        migrations.AddIndex(model_name="arielusercapability", index=models.Index(fields=["identity", "capability_code"], name="ariel_uc_identity_cap_idx")),
        # Constraints
        migrations.AddConstraint(
            model_name="arielidentity",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="active"),
                fields=["learner"],
                name="ariel_one_active_per_learner",
            ),
        ),
        migrations.AddConstraint(
            model_name="arielteachingturn",
            constraint=models.UniqueConstraint(fields=["session", "sequence_number"], name="ariel_tt_unique_session_seq"),
        ),
        migrations.AddConstraint(
            model_name="arielusercapability",
            constraint=models.UniqueConstraint(fields=["user", "identity", "capability_code"], name="ariel_uc_unique"),
        ),
    ]