from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0004_assessment_delivery"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentevaluation",
            name="evaluator_type",
            field=models.CharField(choices=[("deterministic", "Deterministic"), ("human", "Human"), ("ai", "AI"), ("system", "System")], default="deterministic", max_length=50),
        ),
        migrations.AddField(
            model_name="assessmentevaluation",
            name="feedback",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="assessmentevaluation",
            name="is_correct",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assessmentevaluation",
            name="max_score",
            field=models.FloatField(default=1.0),
        ),
        migrations.AddField(
            model_name="assessmentevaluation",
            name="score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name="assessmentresult",
            name="evaluation",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="result", to="assessments.assessmentevaluation"),
        ),
        migrations.AddField(
            model_name="assessmentresult",
            name="attempt",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="result", to="assessments.assessmentattempt"),
        ),
        migrations.AddField(
            model_name="assessmentresult",
            name="max_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="assessmentresult",
            name="passed",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assessmentresult",
            name="percentage",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assessmentresult",
            name="total_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddIndex(
            model_name="assessmentevaluation",
            index=models.Index(fields=["evaluator_type"], name="assessment_eval_type_idx"),
        ),
        migrations.AddIndex(
            model_name="assessmentresult",
            index=models.Index(fields=["attempt"], name="assessment_result_attempt_idx"),
        ),
    ]
