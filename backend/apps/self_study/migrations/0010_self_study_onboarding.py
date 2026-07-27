# Generated for PI-7A conversational onboarding. Do not edit by hand after migration generation is adopted.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("self_study", "0009_self_study_workspace"),
        ("academic", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="curriculumresolutionattempt",
            name="self_study_one_resolution_per_intent_version",
        ),
        migrations.RemoveConstraint(
            model_name="curriculumresolutionattempt",
            name="self_study_resolution_idempotency_unique",
        ),
        migrations.AlterField(
            model_name="curriculumresolutionattempt",
            name="intent",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="curriculum_resolution_attempts", to="self_study.selfstudyintent"),
        ),
        migrations.AlterField(
            model_name="curriculumresolutionattempt",
            name="intent_version",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="CurriculumSubjectBinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("RETIRED", "Retired"), ("INVALIDATED", "Invalidated")], default="ACTIVE", max_length=16)),
                ("authority_note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_curriculum_subject_bindings", to="users.user")),
                ("curriculum_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subject_bindings", to="self_study.curriculumversion")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_curriculum_bindings", to="academic.subject")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_curriculum_subject_bindings", to="users.institution")),
            ],
            options={
                "db_table": "self_study_curriculum_subject_binding",
            },
        ),
        migrations.CreateModel(
            name="SelfStudyOnboarding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("COLLECTING_CONTEXT", "Collecting context"), ("RESOLVING_CURRICULUM", "Resolving curriculum"), ("AWAITING_CURRICULUM_SELECTION", "Awaiting curriculum selection"), ("REVIEWING_SUMMARY", "Reviewing summary"), ("COMPLETED", "Completed"), ("STALE", "Stale"), ("ABANDONED", "Abandoned")], default="COLLECTING_CONTEXT", max_length=40)),
                ("current_stage", models.CharField(choices=[("STUDY_TOPIC", "Study topic"), ("STUDY_INTENT", "Study intent"), ("QUALIFICATION_CONTEXT", "Qualification context"), ("CURRICULUM_DISCOVERY", "Curriculum discovery"), ("CURRICULUM_SELECTION", "Curriculum selection"), ("TARGET_DATE", "Target date"), ("WEEKLY_AVAILABILITY", "Weekly availability"), ("SUMMARY", "Summary"), ("COMPLETED", "Completed")], default="STUDY_TOPIC", max_length=40)),
                ("topic_query", models.CharField(blank=True, max_length=255)),
                ("study_intent", models.CharField(blank=True, choices=[("EXAM", "Study for an exam"), ("LEARN_NEW", "Learn something new"), ("MASTER_SUBJECT", "Learn and master a subject")], max_length=32)),
                ("qualification_query", models.CharField(blank=True, max_length=255)),
                ("jurisdiction_query", models.CharField(blank=True, max_length=64)),
                ("awarding_body_query", models.CharField(blank=True, max_length=128)),
                ("level_query", models.CharField(blank=True, max_length=64)),
                ("target_description", models.CharField(blank=True, max_length=255)),
                ("target_date", models.DateField(blank=True, null=True)),
                ("target_date_known", models.BooleanField(default=False)),
                ("weekly_study_minutes", models.PositiveIntegerField(blank=True, null=True)),
                ("selected_candidate_snapshot", models.JSONField(blank=True, default=dict)),
                ("idempotency_key", models.CharField(blank=True, max_length=128)),
                ("stale_reason", models.CharField(blank=True, max_length=128)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("abandoned_at", models.DateTimeField(blank=True, null=True)),
                ("stale_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("active_resolution_attempt", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="onboarding_sessions", to="self_study.curriculumresolutionattempt")),
                ("created_intent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="onboarding_sessions", to="self_study.selfstudyintent")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_onboardings", to="users.user")),
                ("selected_resolution_candidate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="selected_for_onboardings", to="self_study.curriculumresolutioncandidate")),
                ("selected_curriculum_version", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="selected_for_onboardings", to="self_study.curriculumversion")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_onboardings", to="users.institution")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="onboarding_sessions", to="self_study.selfstudyworkspace")),
            ],
            options={
                "db_table": "self_study_onboarding",
            },
        ),
        migrations.AddIndex(
            model_name="selfstudyonboarding",
            index=models.Index(fields=["learner", "status"], name="ssi_onboard_learner_idx"),
        ),
        migrations.AddIndex(
            model_name="selfstudyonboarding",
            index=models.Index(fields=["workspace", "status"], name="ssi_onboard_workspace_idx"),
        ),
        migrations.AddIndex(
            model_name="selfstudyonboarding",
            index=models.Index(fields=["tenant", "status"], name="ssi_onboard_tenant_idx"),
        ),
        migrations.AddConstraint(
            model_name="selfstudyonboarding",
            constraint=models.UniqueConstraint(condition=~models.Q(idempotency_key=""), fields=("workspace", "idempotency_key"), name="ssi_onboard_idem_unique"),
        ),
        migrations.AddField(
            model_name="curriculumresolutionattempt",
            name="onboarding",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="curriculum_resolution_attempts", to="self_study.selfstudyonboarding"),
        ),
        migrations.AddIndex(
            model_name="curriculumsubjectbinding",
            index=models.Index(fields=["tenant", "status"], name="ssi_cur_subj_tenant_idx"),
        ),
        migrations.AddIndex(
            model_name="curriculumsubjectbinding",
            index=models.Index(fields=["curriculum_version", "status"], name="ssi_cur_subj_ver_idx"),
        ),
        migrations.AddConstraint(
            model_name="curriculumsubjectbinding",
            constraint=models.UniqueConstraint(fields=("curriculum_version", "subject", "tenant"), name="ssi_curr_subj_binding_unique"),
        ),
        migrations.AddConstraint(
            model_name="curriculumresolutionattempt",
            constraint=models.UniqueConstraint(condition=models.Q(intent__isnull=False), fields=("intent", "intent_version", "algorithm_version"), name="self_study_one_resolution_per_intent_version"),
        ),
        migrations.AddConstraint(
            model_name="curriculumresolutionattempt",
            constraint=models.UniqueConstraint(condition=models.Q(intent__isnull=False), fields=("intent", "idempotency_key"), name="self_study_resolution_idempotency_unique"),
        ),
        migrations.AddConstraint(
            model_name="curriculumresolutionattempt",
            constraint=models.UniqueConstraint(condition=models.Q(onboarding__isnull=False), fields=("onboarding", "idempotency_key"), name="ssi_onbd_res_idem_uniq"),
        ),
    ]
