import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("assessments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningEvidence",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_type", models.CharField(choices=[("assessment_attempt", "Assessment Attempt"), ("assessment_result", "Assessment Result"), ("teach_back", "Teach Back"), ("oral_response", "Oral Response"), ("project", "Project"), ("simulation", "Simulation"), ("manual_review", "Manual Review"), ("system", "System")], max_length=50)),
                ("source_id", models.CharField(max_length=255)),
                ("evidence_type", models.CharField(choices=[("correct_response", "Correct Response"), ("partial_understanding", "Partial Understanding"), ("misconception", "Misconception"), ("explanation_quality", "Explanation Quality"), ("applied_reasoning", "Applied Reasoning"), ("completion", "Completion"), ("manual_observation", "Manual Observation"), ("other", "Other")], max_length=50)),
                ("score", models.FloatField(blank=True, null=True)),
                ("confidence", models.FloatField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("content_concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_evidence", to="academic.contentconcept")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_evidence", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "learning_evidence",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="MasteryDecision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("decision", models.CharField(choices=[("not_enough_evidence", "Not Enough Evidence"), ("not_mastered", "Not Mastered"), ("emerging", "Emerging"), ("mastered", "Mastered"), ("needs_review", "Needs Review")], max_length=50)),
                ("confidence", models.FloatField()),
                ("evidence_count", models.PositiveIntegerField()),
                ("rationale", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("content_concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mastery_decisions", to="academic.contentconcept")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mastery_decisions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "mastery_decision",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="MasteryProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("current_decision", models.CharField(choices=[("not_enough_evidence", "Not Enough Evidence"), ("not_mastered", "Not Mastered"), ("emerging", "Emerging"), ("mastered", "Mastered"), ("needs_review", "Needs Review")], max_length=50)),
                ("confidence", models.FloatField()),
                ("evidence_count", models.PositiveIntegerField()),
                ("last_evidence_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("content_concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mastery_profiles", to="academic.contentconcept")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mastery_profiles", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "mastery_profile",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="learningevidence",
            index=models.Index(fields=["learner"], name="learning_evidence_learner_idx"),
        ),
        migrations.AddIndex(
            model_name="learningevidence",
            index=models.Index(fields=["content_concept"], name="learning_evidence_concept_idx"),
        ),
        migrations.AddIndex(
            model_name="learningevidence",
            index=models.Index(fields=["source_type"], name="learning_evidence_source_idx"),
        ),
        migrations.AddIndex(
            model_name="learningevidence",
            index=models.Index(fields=["evidence_type"], name="learning_evidence_type_idx"),
        ),
        migrations.AddIndex(
            model_name="masterydecision",
            index=models.Index(fields=["learner"], name="mastery_decision_learner_idx"),
        ),
        migrations.AddIndex(
            model_name="masterydecision",
            index=models.Index(fields=["content_concept"], name="mastery_decision_concept_idx"),
        ),
        migrations.AddIndex(
            model_name="masterydecision",
            index=models.Index(fields=["decision"], name="mastery_decision_value_idx"),
        ),
        migrations.AddIndex(
            model_name="masteryprofile",
            index=models.Index(fields=["learner"], name="mastery_profile_learner_idx"),
        ),
        migrations.AddIndex(
            model_name="masteryprofile",
            index=models.Index(fields=["content_concept"], name="mastery_profile_concept_idx"),
        ),
        migrations.AddIndex(
            model_name="masteryprofile",
            index=models.Index(fields=["current_decision"], name="mastery_profile_decision_idx"),
        ),
        migrations.AddConstraint(
            model_name="learningevidence",
            constraint=models.CheckConstraint(condition=models.Q(("confidence__gte", 0.0), ("confidence__lte", 1.0)), name="learning_evidence_confidence_0_1"),
        ),
        migrations.AddConstraint(
            model_name="learningevidence",
            constraint=models.CheckConstraint(condition=models.Q(("score__isnull", True), models.Q(("score__gte", 0.0), ("score__lte", 1.0)), _connector="OR"), name="learning_evidence_score_null_or_0_1"),
        ),
        migrations.AddConstraint(
            model_name="masterydecision",
            constraint=models.CheckConstraint(condition=models.Q(("confidence__gte", 0.0), ("confidence__lte", 1.0)), name="mastery_decision_confidence_0_1"),
        ),
        migrations.AddConstraint(
            model_name="masteryprofile",
            constraint=models.UniqueConstraint(fields=("learner", "content_concept"), name="unique_mastery_profile_learner_concept"),
        ),
        migrations.AddConstraint(
            model_name="masteryprofile",
            constraint=models.CheckConstraint(condition=models.Q(("confidence__gte", 0.0), ("confidence__lte", 1.0)), name="mastery_profile_confidence_0_1"),
        ),
    ]
