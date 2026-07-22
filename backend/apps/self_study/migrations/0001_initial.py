import uuid

import apps.self_study.models
import django.db.models.deletion
from django.db import migrations, models

DEFAULT_PLATFORM_POLICY_ID = uuid.UUID("00000000-0000-4000-8000-000000006f01")


def policy_fields():
    return [
        ("automatic_acquisition_enabled", models.BooleanField(default=True)),
        ("allowed_provider_ids", models.JSONField(default=list)),
        ("allowed_source_categories", models.JSONField(default=list)),
        ("allowed_licence_categories", models.JSONField(default=list)),
        ("allowed_mime_types", models.JSONField(default=list)),
        ("allowed_languages", models.JSONField(default=list)),
        ("maximum_resource_count", models.PositiveIntegerField(blank=True, null=True)),
        ("maximum_single_file_bytes", models.PositiveBigIntegerField(blank=True, null=True)),
        ("maximum_total_bytes", models.PositiveBigIntegerField(blank=True, null=True)),
        ("maximum_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
        ("cost_currency", models.CharField(default="USD", max_length=3)),
        ("paid_content_allowed", models.BooleanField(default=False)),
        ("unknown_licence_allowed", models.BooleanField(default=False)),
        ("link_only_when_restricted", models.BooleanField(default=True)),
        ("user_approval_threshold", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
        ("retention_policy", models.CharField(choices=[("DO_NOT_RETAIN", "Do not retain"), ("RETAIN_UNTIL_JOURNEY_END", "Retain until journey end"), ("RETAIN_WITH_JOURNEY", "Retain with journey")], default="RETAIN_WITH_JOURNEY", max_length=64)),
        ("external_network_access_enabled", models.BooleanField(default=False)),
        ("autonomous_curriculum_fallback_allowed", models.BooleanField(default=False)),
    ]


def create_default_platform_policy(apps, schema_editor):
    policy = apps.get_model("self_study", "LearningPolicyRuleSet")
    policy.objects.get_or_create(
        id=DEFAULT_PLATFORM_POLICY_ID,
        defaults={
            "authority": "PLATFORM",
            "version": 1,
            "is_active": True,
            "automatic_acquisition_enabled": True,
            "allowed_provider_ids": [],
            "allowed_source_categories": [],
            "allowed_licence_categories": [],
            "allowed_mime_types": [],
            "allowed_languages": [],
            "paid_content_allowed": False,
            "unknown_licence_allowed": False,
            "link_only_when_restricted": True,
            "retention_policy": "RETAIN_WITH_JOURNEY",
            "external_network_access_enabled": False,
            "autonomous_curriculum_fallback_allowed": False,
        },
    )


def remove_default_platform_policy(apps, schema_editor):
    policy = apps.get_model("self_study", "LearningPolicyRuleSet")
    policy.objects.filter(id=DEFAULT_PLATFORM_POLICY_ID).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("academic", "0006_content_review_fields"),
        ("users", "0004_alter_institution_institution_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EffectiveLearningPolicySnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                *policy_fields(),
                ("policy_version", models.PositiveIntegerField()),
                ("source_policy_ids", models.JSONField(default=list)),
                ("purpose_disclosure_required", models.BooleanField(default=True)),
                ("raw_scores_visible", models.BooleanField(default=False)),
                ("comparative_ranking_allowed", models.BooleanField(default=False)),
                ("learner_can_retake", models.BooleanField(default=True)),
                ("learner_can_challenge", models.BooleanField(default=True)),
                ("learner_can_attempt_checkpoint", models.BooleanField(default=True)),
                ("formal_grade_effect", models.BooleanField(default=False)),
                ("transcript_effect", models.BooleanField(default=False)),
                ("curriculum_source_precedence", models.JSONField(default=apps.self_study.models.default_curriculum_source_precedence)),
                ("external_content_untrusted", models.BooleanField(default=True)),
                ("external_content_can_alter_policy", models.BooleanField(default=False)),
                ("external_content_can_alter_curriculum", models.BooleanField(default=False)),
                ("external_content_can_invoke_tools", models.BooleanField(default=False)),
                ("external_content_can_initiate_downloads", models.BooleanField(default=False)),
                ("external_content_can_grant_trust", models.BooleanField(default=False)),
                ("external_content_can_bypass_governance", models.BooleanField(default=False)),
                ("external_content_can_become_official_without_validation", models.BooleanField(default=False)),
                ("external_content_can_execute", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "self_study_effective_policy_snapshot"},
        ),
        migrations.CreateModel(
            name="LearningPolicyRuleSet",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                *policy_fields(),
                ("authority", models.CharField(choices=[("PLATFORM", "Platform"), ("TENANT", "Tenant"), ("LEARNER", "Learner")], max_length=16)),
                ("version", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("learner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="self_study_policies", to="users.user")),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="self_study_policies", to="users.institution")),
            ],
            options={"db_table": "self_study_policy_rule_set"},
        ),
        migrations.AddConstraint(
            model_name="learningpolicyruleset",
            constraint=models.UniqueConstraint(fields=("authority", "tenant", "learner", "version"), name="self_study_policy_authority_version_unique"),
        ),
        migrations.AddConstraint(
            model_name="learningpolicyruleset",
            constraint=models.UniqueConstraint(condition=models.Q(authority="PLATFORM", is_active=True), fields=("authority",), name="self_study_one_active_platform_policy"),
        ),
        migrations.AddConstraint(
            model_name="learningpolicyruleset",
            constraint=models.UniqueConstraint(condition=models.Q(authority="TENANT", is_active=True), fields=("authority", "tenant"), name="self_study_one_active_tenant_policy"),
        ),
        migrations.AddConstraint(
            model_name="learningpolicyruleset",
            constraint=models.UniqueConstraint(condition=models.Q(authority="LEARNER", is_active=True), fields=("authority", "tenant", "learner"), name="self_study_one_active_learner_policy"),
        ),
        migrations.CreateModel(
            name="SelfStudyIntent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("mode", models.CharField(choices=[("INSTITUTION_GOVERNED", "Institution governed"), ("SELF_STUDY", "Self study")], max_length=32)),
                ("goal_statement", models.TextField(blank=True)),
                ("target_title", models.CharField(blank=True, max_length=255)),
                ("target_outcomes", models.JSONField(blank=True, default=list)),
                ("target_credential", models.CharField(blank=True, max_length=255)),
                ("preferred_curriculum_authority", models.CharField(blank=True, max_length=255)),
                ("jurisdiction", models.CharField(blank=True, max_length=64)),
                ("preferred_language", models.CharField(blank=True, max_length=16)),
                ("learner_age_band", models.CharField(blank=True, max_length=32)),
                ("accessibility_requirements", models.JSONField(blank=True, default=list)),
                ("desired_depth", models.CharField(choices=[("FOUNDATIONAL", "Foundational"), ("GENERAL", "General"), ("ACADEMIC", "Academic"), ("PROFESSIONAL", "Professional"), ("EXAM_PREPARATION", "Exam preparation"), ("SPECIALIST", "Specialist")], default="GENERAL", max_length=32)),
                ("pace_preference", models.CharField(blank=True, max_length=32)),
                ("time_budget_minutes_per_week", models.PositiveIntegerField(blank=True, null=True)),
                ("target_completion_date", models.DateField(blank=True, null=True)),
                ("policy_acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("READY", "Ready"), ("ACTIVE", "Active"), ("SUPERSEDED", "Superseded"), ("CANCELLED", "Cancelled")], default="DRAFT", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_self_study_intents", to="users.user")),
                ("effective_policy_snapshot", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="intent", to="self_study.effectivelearningpolicysnapshot")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_intents", to="users.user")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_intents", to="academic.subject")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_intents", to="users.institution")),
            ],
            options={
                "db_table": "self_study_intent",
                "indexes": [
                    models.Index(fields=["learner", "status"], name="ssi_learner_status_idx"),
                    models.Index(fields=["tenant", "status"], name="ssi_tenant_status_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="selfstudyintent",
            constraint=models.CheckConstraint(
                condition=~models.Q(status="ACTIVE") | models.Q(effective_policy_snapshot__isnull=False),
                name="ssi_active_requires_policy_snapshot",
            ),
        ),
        migrations.CreateModel(
            name="CurriculumResolutionFailure",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("reason_codes", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("intent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="curriculum_resolution_failures", to="self_study.selfstudyintent")),
                ("recorded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recorded_curriculum_failures", to="users.user")),
            ],
            options={"db_table": "self_study_curriculum_resolution_failure"},
        ),
        migrations.CreateModel(
            name="ResourceAcquisitionDecision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("decision", models.CharField(max_length=32)),
                ("reason_codes", models.JSONField(default=list)),
                ("candidate_metadata", models.JSONField(default=dict)),
                ("candidate_fingerprint", models.CharField(max_length=64)),
                ("canonical_uri", models.URLField(blank=True, max_length=2048)),
                ("provider_id", models.CharField(max_length=255)),
                ("content_hash", models.CharField(blank=True, max_length=128)),
                ("acquisition_method", models.CharField(default="POLICY_AUTHORIZATION_ONLY", max_length=32)),
                ("idempotency_key", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("decided_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="resource_acquisition_decisions", to="users.user")),
                ("intent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acquisition_decisions", to="self_study.selfstudyintent")),
                ("policy_snapshot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acquisition_decisions", to="self_study.effectivelearningpolicysnapshot")),
            ],
            options={"db_table": "self_study_resource_acquisition_decision"},
        ),
        migrations.AddConstraint(
            model_name="resourceacquisitiondecision",
            constraint=models.UniqueConstraint(fields=("intent", "idempotency_key"), name="ssi_acquisition_idempotency_unique"),
        ),
        migrations.CreateModel(
            name="AutonomousFallbackDecision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("authorized", models.BooleanField(default=False)),
                ("reason_codes", models.JSONField(default=list)),
                ("idempotency_key", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("decided_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="autonomous_fallback_decisions", to="users.user")),
                ("intent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="autonomous_fallback_decisions", to="self_study.selfstudyintent")),
                ("policy_snapshot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="autonomous_fallback_decisions", to="self_study.effectivelearningpolicysnapshot")),
                ("resolution_failure", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="fallback_decisions", to="self_study.curriculumresolutionfailure")),
            ],
            options={"db_table": "self_study_autonomous_fallback_decision"},
        ),
        migrations.AddConstraint(
            model_name="autonomousfallbackdecision",
            constraint=models.UniqueConstraint(fields=("intent", "idempotency_key"), name="ssi_fallback_idempotency_unique"),
        ),
        migrations.RunPython(create_default_platform_policy, remove_default_platform_policy),
    ]
