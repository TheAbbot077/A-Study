import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("academic", "0006_content_review_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Assessment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("active", "Active"),
                            ("submitted", "Submitted"),
                            ("evaluated", "Evaluated"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="created",
                        max_length=50,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "content_concept",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assessments",
                        to="academic.contentconcept",
                    ),
                ),
            ],
            options={"db_table": "assessment", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AssessmentItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "item_type",
                    models.CharField(
                        choices=[
                            ("multiple_choice", "Multiple Choice"),
                            ("short_answer", "Short Answer"),
                            ("essay", "Essay"),
                            ("calculation", "Calculation"),
                            ("matching", "Matching"),
                            ("ordering", "Ordering"),
                            ("true_false", "True/False"),
                            ("diagram", "Diagram"),
                            ("oral", "Oral"),
                            ("teach_back", "Teach Back"),
                            ("programming", "Programming"),
                            ("clinical", "Clinical"),
                            ("interview", "Interview"),
                            ("other", "Other"),
                        ],
                        max_length=50,
                    ),
                ),
                ("prompt", models.TextField()),
                ("sequence_number", models.PositiveIntegerField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="assessments.assessment",
                    ),
                ),
            ],
            options={"db_table": "assessment_item", "ordering": ["sequence_number"]},
        ),
        migrations.CreateModel(
            name="AssessmentAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("active", "Active"),
                            ("submitted", "Submitted"),
                            ("evaluated", "Evaluated"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="active",
                        max_length=50,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="assessments.assessment",
                    ),
                ),
                (
                    "learner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assessment_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "assessment_attempt", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AssessmentInteraction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("interaction_type", models.CharField(max_length=100)),
                ("content", models.TextField(blank=True)),
                ("sequence_number", models.PositiveIntegerField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interactions",
                        to="assessments.assessmentattempt",
                    ),
                ),
            ],
            options={"db_table": "assessment_interaction", "ordering": ["sequence_number"]},
        ),
        migrations.CreateModel(
            name="AssessmentResponse",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("response_data", models.JSONField(blank=True, default=dict)),
                ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="assessments.assessmentattempt",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="assessments.assessmentitem",
                    ),
                ),
            ],
            options={"db_table": "assessment_response", "ordering": ["submitted_at"]},
        ),
        migrations.CreateModel(
            name="AssessmentEvaluation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("evaluation_data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "evaluator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assessment_evaluations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "response",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evaluation",
                        to="assessments.assessmentresponse",
                    ),
                ),
            ],
            options={"db_table": "assessment_evaluation"},
        ),
        migrations.CreateModel(
            name="AssessmentResult",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("result_data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "evaluation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="result",
                        to="assessments.assessmentevaluation",
                    ),
                ),
            ],
            options={"db_table": "assessment_result"},
        ),
        migrations.AddIndex(model_name="assessment", index=models.Index(fields=["content_concept"], name="assess_concept_idx")),
        migrations.AddIndex(model_name="assessment", index=models.Index(fields=["state"], name="assess_state_idx")),
        migrations.AddIndex(model_name="assessmentattempt", index=models.Index(fields=["assessment"], name="assess_attempt_assess_idx")),
        migrations.AddIndex(model_name="assessmentattempt", index=models.Index(fields=["learner"], name="assess_attempt_learner_idx")),
        migrations.AddIndex(model_name="assessmentattempt", index=models.Index(fields=["state"], name="assess_attempt_state_idx")),
        migrations.AddConstraint(
            model_name="assessmentitem",
            constraint=models.UniqueConstraint(fields=("assessment", "sequence_number"), name="unique_assessment_item_sequence"),
        ),
        migrations.AddConstraint(
            model_name="assessmentitem",
            constraint=models.CheckConstraint(condition=models.Q(("sequence_number__gte", 1)), name="assessment_item_sequence_gte_1"),
        ),
        migrations.AddConstraint(
            model_name="assessmentinteraction",
            constraint=models.UniqueConstraint(fields=("attempt", "sequence_number"), name="unique_assessment_interaction_sequence"),
        ),
        migrations.AddConstraint(
            model_name="assessmentinteraction",
            constraint=models.CheckConstraint(condition=models.Q(("sequence_number__gte", 1)), name="assessment_interaction_sequence_gte_1"),
        ),
        migrations.AddConstraint(
            model_name="assessmentresponse",
            constraint=models.UniqueConstraint(fields=("attempt", "item"), name="unique_attempt_item_response"),
        ),
    ]
