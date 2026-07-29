from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0006_evidence_integration_source"),
        ("learning_journeys", "0002_learning_journey_action_receipt"),
        ("self_study", "0010_self_study_onboarding"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningCompetencyProgress",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("NOT_STARTED", "Not started"),
                            ("EMERGING", "Emerging"),
                            ("DEVELOPING", "Developing"),
                            ("DEMONSTRATED", "Demonstrated"),
                            ("REINFORCED", "Reinforced"),
                            ("REVIEW_REQUIRED", "Review required"),
                            ("REGRESSED", "Regressed"),
                            ("SUPERSEDED", "Superseded"),
                        ],
                        default="NOT_STARTED",
                        max_length=24,
                    ),
                ),
                (
                    "unlock_state",
                    models.CharField(
                        choices=[
                            ("LOCKED", "Locked"),
                            ("AVAILABLE", "Available"),
                            ("ACTIVE", "Active"),
                            ("COMPLETED", "Completed"),
                            ("SUPERSEDED", "Superseded"),
                        ],
                        default="LOCKED",
                        max_length=16,
                    ),
                ),
                ("latest_evidence_summary", models.JSONField(blank=True, default=dict)),
                ("unlocked_at", models.DateTimeField(blank=True, null=True)),
                ("first_demonstrated_at", models.DateTimeField(blank=True, null=True)),
                ("last_progressed_at", models.DateTimeField(blank=True, null=True)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "competency",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_journey_progress", to="self_study.curriculumnode"),
                ),
                (
                    "journey",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="competency_progress", to="learning_journeys.learningjourney"),
                ),
                (
                    "latest_mastery_decision",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="learning_competency_progress",
                        to="assessments.masterydecision",
                    ),
                ),
                (
                    "superseded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="superseded_learning_progress",
                        to="self_study.curriculumnode",
                    ),
                ),
            ],
            options={
                "db_table": "learning_competency_progress",
            },
        ),
        migrations.CreateModel(
            name="LearningCompetencyProgressHistory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "old_state",
                    models.CharField(
                        choices=[
                            ("NOT_STARTED", "Not started"),
                            ("EMERGING", "Emerging"),
                            ("DEVELOPING", "Developing"),
                            ("DEMONSTRATED", "Demonstrated"),
                            ("REINFORCED", "Reinforced"),
                            ("REVIEW_REQUIRED", "Review required"),
                            ("REGRESSED", "Regressed"),
                            ("SUPERSEDED", "Superseded"),
                        ],
                        max_length=24,
                    ),
                ),
                (
                    "new_state",
                    models.CharField(
                        choices=[
                            ("NOT_STARTED", "Not started"),
                            ("EMERGING", "Emerging"),
                            ("DEVELOPING", "Developing"),
                            ("DEMONSTRATED", "Demonstrated"),
                            ("REINFORCED", "Reinforced"),
                            ("REVIEW_REQUIRED", "Review required"),
                            ("REGRESSED", "Regressed"),
                            ("SUPERSEDED", "Superseded"),
                        ],
                        max_length=24,
                    ),
                ),
                (
                    "old_unlock_state",
                    models.CharField(
                        choices=[
                            ("LOCKED", "Locked"),
                            ("AVAILABLE", "Available"),
                            ("ACTIVE", "Active"),
                            ("COMPLETED", "Completed"),
                            ("SUPERSEDED", "Superseded"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "new_unlock_state",
                    models.CharField(
                        choices=[
                            ("LOCKED", "Locked"),
                            ("AVAILABLE", "Available"),
                            ("ACTIVE", "Active"),
                            ("COMPLETED", "Completed"),
                            ("SUPERSEDED", "Superseded"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("INITIALIZED", "Initialized"),
                            ("MASTERY_EMERGING", "Mastery emerging"),
                            ("MASTERY_DEMONSTRATED", "Mastery demonstrated"),
                            ("MASTERY_REINFORCED", "Mastery reinforced"),
                            ("REVIEW_REQUIRED", "Review required"),
                            ("REGRESSION_EVIDENCE", "Regression evidence"),
                            ("CURRICULUM_SUPERSEDED", "Curriculum superseded"),
                            ("UNCHANGED", "Unchanged"),
                        ],
                        max_length=48,
                    ),
                ),
                ("triggering_evidence_id", models.UUIDField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="learning_competency_progress_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "competency",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_progress_history", to="self_study.curriculumnode"),
                ),
                (
                    "journey",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="competency_progress_history", to="learning_journeys.learningjourney"),
                ),
                (
                    "progress",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="history", to="learning_journeys.learningcompetencyprogress"),
                ),
                (
                    "triggering_mastery_decision",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="learning_competency_progress_history",
                        to="assessments.masterydecision",
                    ),
                ),
            ],
            options={
                "db_table": "learning_competency_progress_history",
            },
        ),
        migrations.AddConstraint(
            model_name="learningcompetencyprogress",
            constraint=models.UniqueConstraint(fields=("journey", "competency"), name="lj_competency_progress_unique"),
        ),
        migrations.AddIndex(
            model_name="learningcompetencyprogress",
            index=models.Index(fields=["journey", "state"], name="lj_comp_progress_state_idx"),
        ),
        migrations.AddIndex(
            model_name="learningcompetencyprogress",
            index=models.Index(fields=["journey", "unlock_state"], name="lj_comp_unlock_state_idx"),
        ),
        migrations.AddIndex(
            model_name="learningcompetencyprogress",
            index=models.Index(fields=["competency", "state"], name="lj_competency_state_idx"),
        ),
        migrations.AddIndex(
            model_name="learningcompetencyprogresshistory",
            index=models.Index(fields=["journey", "created_at"], name="lj_comp_hist_journey_time_idx"),
        ),
        migrations.AddIndex(
            model_name="learningcompetencyprogresshistory",
            index=models.Index(fields=["competency", "new_state"], name="lj_comp_hist_state_idx"),
        ),
    ]
