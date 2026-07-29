from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0006_content_review_fields"),
        ("learning_journeys", "0003_competency_progression"),
        ("self_study", "0010_self_study_onboarding"),
        ("users", "0004_alter_institution_institution_type_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="learningjourneysourcebinding",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("SELF_STUDY_WORKSPACE", "Self-study workspace"),
                    ("INSTITUTION_MEMBERSHIP", "Institution membership"),
                    ("INSTITUTIONAL_ASSIGNMENT", "Institutional assignment"),
                ],
                max_length=40,
            ),
        ),
        migrations.CreateModel(
            name="InstitutionalLearningAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "assignment_state",
                    models.CharField(
                        choices=[
                            ("ASSIGNED", "Assigned"),
                            ("ACCEPTED", "Accepted"),
                            ("ACTIVE", "Active"),
                            ("ON_HOLD", "On hold"),
                            ("INTERVENTION_REQUIRED", "Intervention required"),
                            ("COMPLETION_PENDING", "Completion pending"),
                            ("COMPLETED", "Completed"),
                            ("WITHDRAWN", "Withdrawn"),
                        ],
                        default="ASSIGNED",
                        max_length=32,
                    ),
                ),
                (
                    "acceptance_mode",
                    models.CharField(
                        choices=[
                            ("AUTO_ACCEPT", "Auto accept"),
                            ("LEARNER_CONFIRMATION_REQUIRED", "Learner confirmation required"),
                            ("ADMIN_CONFIRMATION_REQUIRED", "Admin confirmation required"),
                        ],
                        default="AUTO_ACCEPT",
                        max_length=40,
                    ),
                ),
                (
                    "completion_state",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("READY", "Ready"), ("COMPLETED", "Completed"), ("BLOCKED", "Blocked")],
                        default="PENDING",
                        max_length=24,
                    ),
                ),
                ("programme_label", models.CharField(blank=True, max_length=255)),
                ("course_label", models.CharField(blank=True, max_length=255)),
                ("delivery_objectives", models.JSONField(blank=True, default=dict)),
                ("required_competency_ids", models.JSONField(blank=True, default=list)),
                ("visibility_policy", models.JSONField(blank=True, default=dict)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("withdrawn_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "assigned_by",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_institutional_learning_assignments", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "curriculum_reference",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="institutional_learning_assignments",
                        to="self_study.curriculumreference",
                    ),
                ),
                (
                    "institution",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_assignments", to="users.institution"),
                ),
                (
                    "journey",
                    models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="institutional_assignment", to="learning_journeys.learningjourney"),
                ),
                (
                    "learner",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="institutional_learning_assignments", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "membership",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_assignments", to="users.institutionmembership"),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="institutional_learning_assignments",
                        to="academic.subject",
                    ),
                ),
            ],
            options={
                "db_table": "institutional_learning_assignment",
            },
        ),
        migrations.CreateModel(
            name="InstitutionalInterventionRecommendation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("REPEATED_REVIEW_REQUIRED", "Repeated review required"),
                            ("PERSISTENT_REGRESSION", "Persistent regression"),
                            ("REQUIRED_COMPETENCY_OVERDUE", "Required competency overdue"),
                            ("LEARNING_INACTIVITY", "Learning inactivity"),
                        ],
                        max_length=48,
                    ),
                ),
                (
                    "severity",
                    models.CharField(choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")], default="MEDIUM", max_length=16),
                ),
                ("recommended_action", models.CharField(max_length=500)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Open"),
                            ("ACKNOWLEDGED", "Acknowledged"),
                            ("IN_PROGRESS", "In progress"),
                            ("RESOLVED", "Resolved"),
                            ("DISMISSED", "Dismissed"),
                        ],
                        default="OPEN",
                        max_length=24,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assignment",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="interventions", to="learning_journeys.institutionallearningassignment"),
                ),
                (
                    "institution",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_interventions", to="users.institution"),
                ),
                (
                    "journey",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="institutional_interventions", to="learning_journeys.learningjourney"),
                ),
                (
                    "learner",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="institutional_learning_interventions", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "resolved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="resolved_institutional_learning_interventions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "triggering_progress",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="institutional_interventions",
                        to="learning_journeys.learningcompetencyprogress",
                    ),
                ),
            ],
            options={
                "db_table": "institutional_intervention_recommendation",
            },
        ),
        migrations.AddIndex(
            model_name="institutionallearningassignment",
            index=models.Index(fields=["institution", "assignment_state"], name="ila_institution_state_idx"),
        ),
        migrations.AddIndex(
            model_name="institutionallearningassignment",
            index=models.Index(fields=["learner", "assignment_state"], name="ila_learner_state_idx"),
        ),
        migrations.AddIndex(
            model_name="institutionallearningassignment",
            index=models.Index(fields=["journey", "completion_state"], name="ila_journey_completion_idx"),
        ),
        migrations.AddIndex(
            model_name="institutionalinterventionrecommendation",
            index=models.Index(fields=["institution", "status"], name="iir_institution_status_idx"),
        ),
        migrations.AddIndex(
            model_name="institutionalinterventionrecommendation",
            index=models.Index(fields=["journey", "reason"], name="iir_journey_reason_idx"),
        ),
    ]
