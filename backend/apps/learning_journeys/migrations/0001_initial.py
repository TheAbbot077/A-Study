import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0004_alter_institution_institution_type_and_more"),
        ("academic", "0001_initial"),
        ("self_study", "0010_self_study_onboarding"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningJourney",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("journey_type", models.CharField(choices=[("SELF_STUDY", "Self-study"), ("INSTITUTIONAL", "Institutional")], max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("CREATED", "Created"),
                            ("DISCOVERING_GOAL", "Discovering goal"),
                            ("INTENT_CONFIRMED", "Intent confirmed"),
                            ("RESOLVING_CURRICULUM", "Resolving curriculum"),
                            ("CURRICULUM_UNRESOLVED", "Curriculum unresolved"),
                            ("CURRICULUM_MATCHED", "Curriculum matched"),
                            ("SUBJECT_BINDING_REQUIRED", "Subject binding required"),
                            ("SUBJECT_BINDING_UNAVAILABLE", "Subject binding unavailable"),
                            ("SUBJECT_BOUND", "Subject bound"),
                            ("STARTING_STATE_REQUIRED", "Starting state required"),
                            ("STARTING_STATE_IN_PROGRESS", "Starting state in progress"),
                            ("STARTING_STATE_CONFIRMED", "Starting state confirmed"),
                            ("BRIDGE_REQUIRED", "Bridge required"),
                            ("PLAN_REQUIRED", "Plan required"),
                            ("PLAN_READY", "Plan ready"),
                            ("LEARNING_ACTIVE", "Learning active"),
                            ("LEARNING_BLOCKED", "Learning blocked"),
                            ("PAUSED", "Paused"),
                            ("LEARNING_GOAL_COMPLETED", "Learning goal completed"),
                            ("WITHDRAWN", "Withdrawn"),
                            ("ARCHIVED", "Archived"),
                        ],
                        default="CREATED",
                        max_length=40,
                    ),
                ),
                (
                    "status_reason_code",
                    models.CharField(
                        choices=[
                            ("JOURNEY_CREATED", "Journey created"),
                            ("INTENT_NOT_CONFIRMED", "Intent not confirmed"),
                            ("CURRICULUM_RESOLUTION_PENDING", "Curriculum resolution pending"),
                            ("NO_GOVERNED_CURRICULUM", "No governed curriculum"),
                            ("CURRICULUM_SELECTION_REQUIRED", "Curriculum selection required"),
                            ("SELF_STUDY_BINDING_MISSING", "Self-study binding missing"),
                            ("DIAGNOSTIC_REQUIRED", "Diagnostic required"),
                            ("DIAGNOSTIC_IN_PROGRESS", "Diagnostic in progress"),
                            ("PLACEMENT_PENDING", "Placement pending"),
                            ("BRIDGE_PLAN_REQUIRED", "Bridge plan required"),
                            ("LEARNING_PLAN_REQUIRED", "Learning plan required"),
                            ("TEACHING_NOT_READY", "Teaching not ready"),
                            ("ACTIVE_REMEDIATION", "Active remediation"),
                            ("MANUALLY_PAUSED", "Manually paused"),
                            ("GOAL_COMPLETED", "Goal completed"),
                            ("WITHDRAWN_BY_LEARNER", "Withdrawn by learner"),
                            ("ARCHIVED_BY_POLICY", "Archived by policy"),
                            ("INSTITUTIONAL_ASSIGNMENT_REQUIRED", "Institutional assignment required"),
                        ],
                        default="JOURNEY_CREATED",
                        max_length=64,
                    ),
                ),
                ("status_reason_message", models.CharField(blank=True, max_length=500)),
                ("current_step_code", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("paused_at", models.DateTimeField(blank=True, null=True)),
                ("withdrawn_at", models.DateTimeField(blank=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("last_synchronized_at", models.DateTimeField(blank=True, null=True)),
                ("projection_version", models.PositiveIntegerField(default=1)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "institution",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="learning_journeys",
                        to="users.institution",
                    ),
                ),
                (
                    "learner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="learning_journeys",
                        to="users.user",
                    ),
                ),
            ],
            options={"db_table": "learning_journey"},
        ),
        migrations.CreateModel(
            name="LearningJourneyCapabilityReferences",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("intent_id", models.UUIDField(blank=True, null=True)),
                ("curriculum_resolution_attempt_id", models.UUIDField(blank=True, null=True)),
                ("diagnostic_id", models.UUIDField(blank=True, null=True)),
                ("placement_id", models.UUIDField(blank=True, null=True)),
                ("bridge_plan_id", models.UUIDField(blank=True, null=True)),
                ("learning_plan_id", models.UUIDField(blank=True, null=True)),
                ("teaching_preparation_id", models.UUIDField(blank=True, null=True)),
                ("active_teaching_session_id", models.UUIDField(blank=True, null=True)),
                ("remediation_plan_id", models.UUIDField(blank=True, null=True)),
                ("references_snapshot", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "journey",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="capability_references",
                        to="learning_journeys.learningjourney",
                    ),
                ),
            ],
            options={"db_table": "learning_journey_capability_references"},
        ),
        migrations.CreateModel(
            name="LearningJourneySourceBinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "source_type",
                    models.CharField(
                        choices=[("SELF_STUDY_WORKSPACE", "Self-study workspace"), ("INSTITUTION_MEMBERSHIP", "Institution membership")],
                        max_length=40,
                    ),
                ),
                ("source_id", models.UUIDField()),
                ("source_version", models.PositiveIntegerField(blank=True, null=True)),
                ("bound_at", models.DateTimeField(auto_now_add=True)),
                (
                    "journey",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="source_bindings",
                        to="learning_journeys.learningjourney",
                    ),
                ),
            ],
            options={"db_table": "learning_journey_source_binding"},
        ),
        migrations.CreateModel(
            name="LearningJourneySubjectBinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "binding_source",
                    models.CharField(
                        choices=[
                            ("SELF_STUDY_CURRICULUM_RESOLUTION", "Self-study curriculum resolution"),
                            ("INSTITUTIONAL_ASSIGNMENT", "Institutional assignment"),
                            ("ADMINISTRATIVE_REPAIR", "Administrative repair"),
                        ],
                        max_length=48,
                    ),
                ),
                ("binding_authority_id", models.UUIDField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("SUPERSEDED", "Superseded"), ("INVALIDATED", "Invalidated")],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("bound_at", models.DateTimeField(auto_now_add=True)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "curriculum_reference",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="learning_journey_subject_bindings",
                        to="self_study.curriculumreference",
                    ),
                ),
                (
                    "journey",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subject_bindings",
                        to="learning_journeys.learningjourney",
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="learning_journey_bindings",
                        to="academic.subject",
                    ),
                ),
            ],
            options={"db_table": "learning_journey_subject_binding"},
        ),
        migrations.AddIndex(model_name="learningjourney", index=models.Index(fields=["learner", "status"], name="lj_learner_status_idx")),
        migrations.AddIndex(model_name="learningjourney", index=models.Index(fields=["institution", "status"], name="lj_institution_status_idx")),
        migrations.AddIndex(model_name="learningjourney", index=models.Index(fields=["journey_type", "status"], name="lj_type_status_idx")),
        migrations.AddConstraint(
            model_name="learningjourney",
            constraint=models.CheckConstraint(
                condition=models.Q(journey_type="INSTITUTIONAL", institution__isnull=False) | models.Q(journey_type="SELF_STUDY"),
                name="lj_institutional_requires_institution",
            ),
        ),
        migrations.AddConstraint(
            model_name="learningjourneysourcebinding",
            constraint=models.UniqueConstraint(fields=("source_type", "source_id"), name="lj_source_unique"),
        ),
        migrations.AddConstraint(
            model_name="learningjourneysourcebinding",
            constraint=models.UniqueConstraint(fields=("journey", "source_type"), name="lj_source_type_per_journey_unique"),
        ),
        migrations.AddIndex(
            model_name="learningjourneysourcebinding",
            index=models.Index(fields=["source_type", "source_id"], name="lj_source_lookup_idx"),
        ),
        migrations.AddConstraint(
            model_name="learningjourneysubjectbinding",
            constraint=models.UniqueConstraint(fields=("journey",), condition=models.Q(status="ACTIVE"), name="lj_one_active_subject_binding"),
        ),
        migrations.AddIndex(
            model_name="learningjourneysubjectbinding",
            index=models.Index(fields=["journey", "status"], name="lj_subj_binding_status_idx"),
        ),
    ]
