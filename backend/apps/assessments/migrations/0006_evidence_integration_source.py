from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0005_evaluation_grading"),
    ]

    operations = [
        migrations.AlterField(
            model_name="learningevidence",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("assessment_attempt", "Assessment Attempt"),
                    ("assessment_evaluation", "Assessment Evaluation"),
                    ("assessment_result", "Assessment Result"),
                    ("teach_back", "Teach Back"),
                    ("oral_response", "Oral Response"),
                    ("project", "Project"),
                    ("simulation", "Simulation"),
                    ("manual_review", "Manual Review"),
                    ("system", "System"),
                ],
                max_length=50,
            ),
        ),
    ]
