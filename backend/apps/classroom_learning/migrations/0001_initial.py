from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("users", "0004_alter_institution_institution_type_and_more"),
        ("educational_organization", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LessonPreparation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("topic_reference", models.CharField(blank=True, max_length=255)),
                ("lesson_date", models.DateField(blank=True, null=True)),
                ("learning_objective", models.TextField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("ready", "Ready"), ("published", "Published"), ("cancelled", "Cancelled"), ("completed", "Completed"), ("archived", "Archived")], default="draft", max_length=24)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name="PreparednessActivity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("purpose", models.CharField(default="LESSON_PREPARATION", max_length=64)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("open", "Open"), ("closed", "Closed"), ("cancelled", "Cancelled"), ("archived", "Archived")], default="draft", max_length=24)),
                ("instructions", models.TextField(blank=True)),
                ("available_from", models.DateTimeField(blank=True, null=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="preparedness_activities", to=settings.AUTH_USER_MODEL)),
                ("lesson_preparation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="activities", to="classroom_learning.lessonpreparation")),
            ],
        ),
        migrations.CreateModel(
            name="ClassPreparednessAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("open", "Open"), ("closed", "Closed"), ("cancelled", "Cancelled"), ("archived", "Archived")], default="published", max_length=24)),
                ("available_from", models.DateTimeField(blank=True, null=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("activity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assignments", to="classroom_learning.preparednessactivity")),
                ("class_group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="preparedness_assignments", to="educational_organization.classgroup")),
                ("course_offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="preparedness_assignments", to="educational_organization.courseoffering")),
                ("institution", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="preparedness_assignments", to="users.institution")),
            ],
        ),
        migrations.CreateModel(
            name="LessonPrerequisite",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("authority_type", models.CharField(max_length=64)),
                ("authority_reference", models.CharField(max_length=255)),
                ("priority", models.CharField(choices=[("required", "Required"), ("important", "Important"), ("helpful", "Helpful")], default="important", max_length=16)),
                ("sequence", models.PositiveIntegerField(default=1)),
                ("teacher_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("lesson_preparation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="prerequisites", to="classroom_learning.lessonpreparation")),
            ],
        ),
        migrations.CreateModel(
            name="PreparednessPrompt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sequence", models.PositiveIntegerField(default=1)),
                ("prompt_type", models.CharField(choices=[("explanation", "Explanation"), ("example", "Example"), ("comparison", "Comparison"), ("diagram", "Diagram"), ("what_if", "What If"), ("short_application", "Short Application"), ("ariel_attempt", "Ariel Attempt")], max_length=32)),
                ("prompt_text", models.TextField()),
                ("prerequisite_reference", models.CharField(blank=True, max_length=255)),
                ("required", models.BooleanField(default=False)),
                ("ariel_eligible", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("activity", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="prompts", to="classroom_learning.preparednessactivity")),
            ],
        ),
        migrations.CreateModel(
            name="LearnerPreparednessParticipation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("assigned", "Assigned"), ("open", "Open"), ("started", "Started"), ("responded", "Responded"), ("completed", "Completed"), ("declined", "Declined"), ("expired", "Expired")], default="assigned", max_length=24)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("ariel_opted_in_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="participations", to="classroom_learning.classpreparednessassignment")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="preparedness_participations", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ArielPreparednessAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("ariel_identity_id", models.UUIDField()),
                ("status", models.CharField(choices=[("created", "Created"), ("ready", "Ready"), ("attempted", "Attempted"), ("completed", "Completed"), ("insufficient_memory", "Insufficient Memory"), ("conflicted_memory", "Conflicted Memory"), ("excluded", "Excluded"), ("failed", "Failed")], default="created", max_length=32)),
                ("constitution_version", models.CharField(blank=True, max_length=32)),
                ("policy_version", models.CharField(blank=True, max_length=32)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("signal_classifications", models.JSONField(blank=True, default=list)),
                ("safe_summary_metadata", models.JSONField(blank=True, default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_preparedness_attempts", to=settings.AUTH_USER_MODEL)),
                ("participation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_attempts", to="classroom_learning.learnerpreparednessparticipation")),
                ("prompt", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ariel_attempts", to="classroom_learning.preparednessprompt")),
            ],
        ),
        migrations.AddConstraint(
            model_name="lessonprerequisite",
            constraint=models.UniqueConstraint(fields=("lesson_preparation", "sequence"), name="classroom_lesson_prereq_sequence_unique"),
        ),
        migrations.AddConstraint(
            model_name="preparednessprompt",
            constraint=models.UniqueConstraint(fields=("activity", "sequence"), name="classroom_preparedness_prompt_sequence_unique"),
        ),
        migrations.AddConstraint(
            model_name="learnerpreparednessparticipation",
            constraint=models.UniqueConstraint(fields=("assignment", "learner"), name="classroom_participation_unique"),
        ),
        migrations.AddConstraint(
            model_name="arielpreparednessattempt",
            constraint=models.UniqueConstraint(fields=("participation", "prompt"), name="classroom_ariel_attempt_unique"),
        ),
    ]
