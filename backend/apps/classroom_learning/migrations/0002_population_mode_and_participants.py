from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classroom_learning", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="classpreparednessassignment",
            name="population_mode",
            field=models.CharField(choices=[("explicit_participants", "Explicit Participants"), ("class_roster", "Class Roster")], default="explicit_participants", max_length=32),
        ),
        migrations.AddField(
            model_name="classpreparednessassignment",
            name="population_source",
            field=models.CharField(default="PREPAREDNESS_PARTICIPATION_RECORDS", max_length=128),
        ),
        migrations.AddConstraint(
            model_name="classpreparednessassignment",
            constraint=models.UniqueConstraint(fields=("activity", "class_group"), name="classroom_assignment_unique"),
        ),
    ]
