from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pedagogicalmessage",
            name="message_type",
            field=models.CharField(
                choices=[
                    ("explanation", "Explanation"),
                    ("question", "Question"),
                    ("response", "Response"),
                    ("clarification", "Clarification"),
                    ("summary", "Summary"),
                    ("learner_question", "Learner Question"),
                    ("acknowledgement", "Acknowledgement"),
                    ("reflection", "Reflection"),
                    ("transition", "Transition"),
                    ("presence", "Presence"),
                    ("encouragement", "Encouragement"),
                    ("reflection_prompt", "Reflection Prompt"),
                    ("clarification_prompt", "Clarification Prompt"),
                    ("learning_check", "Learning Check"),
                    ("session_summary", "Session Summary"),
                    ("system", "System"),
                ],
                max_length=50,
            ),
        ),
    ]
