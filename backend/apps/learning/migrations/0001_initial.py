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
            name="PedagogicalSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("active", "Active"),
                            ("paused", "Paused"),
                            ("completed", "Completed"),
                            ("abandoned", "Abandoned"),
                        ],
                        default="created",
                        max_length=50,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "content_concept",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pedagogical_sessions",
                        to="academic.contentconcept",
                    ),
                ),
                (
                    "learner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pedagogical_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "learning_pedagogical_session",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PedagogicalMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "sender_type",
                    models.CharField(
                        choices=[
                            ("learner", "Learner"),
                            ("abbot", "Abbot"),
                            ("ariel", "Ariel"),
                            ("system", "System"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "message_type",
                    models.CharField(
                        choices=[
                            ("explanation", "Explanation"),
                            ("question", "Question"),
                            ("response", "Response"),
                            ("clarification", "Clarification"),
                            ("summary", "Summary"),
                            ("system", "System"),
                        ],
                        max_length=50,
                    ),
                ),
                ("content", models.TextField()),
                ("sequence_number", models.PositiveIntegerField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "pedagogical_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="learning.pedagogicalsession",
                    ),
                ),
            ],
            options={
                "db_table": "learning_pedagogical_message",
                "ordering": ["sequence_number"],
            },
        ),
        migrations.AddIndex(
            model_name="pedagogicalsession",
            index=models.Index(fields=["learner"], name="learn_session_learner_idx"),
        ),
        migrations.AddIndex(
            model_name="pedagogicalsession",
            index=models.Index(fields=["content_concept"], name="learn_session_concept_idx"),
        ),
        migrations.AddIndex(
            model_name="pedagogicalsession",
            index=models.Index(fields=["status"], name="learn_session_status_idx"),
        ),
        migrations.AddIndex(
            model_name="pedagogicalmessage",
            index=models.Index(fields=["pedagogical_session"], name="learn_msg_session_idx"),
        ),
        migrations.AddIndex(
            model_name="pedagogicalmessage",
            index=models.Index(fields=["sender_type"], name="learn_msg_sender_idx"),
        ),
        migrations.AddIndex(
            model_name="pedagogicalmessage",
            index=models.Index(fields=["message_type"], name="learn_msg_type_idx"),
        ),
        migrations.AddConstraint(
            model_name="pedagogicalmessage",
            constraint=models.UniqueConstraint(
                fields=("pedagogical_session", "sequence_number"),
                name="unique_pedagogical_session_sequence",
            ),
        ),
        migrations.AddConstraint(
            model_name="pedagogicalmessage",
            constraint=models.CheckConstraint(
                condition=models.Q(("sequence_number__gte", 1)),
                name="pedagogical_message_sequence_gte_1",
            ),
        ),
    ]
