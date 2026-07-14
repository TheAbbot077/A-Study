import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("assessments", "0002_evidence_mastery"),
    ]

    operations = [
        migrations.CreateModel(
            name="ItemBankEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("item_type", models.CharField(choices=[("multiple_choice", "Multiple Choice"), ("short_answer", "Short Answer"), ("essay", "Essay"), ("calculation", "Calculation"), ("matching", "Matching"), ("ordering", "Ordering"), ("true_false", "True/False"), ("diagram", "Diagram"), ("oral", "Oral"), ("teach_back", "Teach Back"), ("programming", "Programming"), ("clinical", "Clinical"), ("interview", "Interview"), ("other", "Other")], max_length=50)),
                ("prompt", models.TextField()),
                ("explanation", models.TextField(blank=True)),
                ("difficulty", models.CharField(choices=[("unknown", "Unknown"), ("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"), ("advanced", "Advanced")], default="unknown", max_length=50)),
                ("review_status", models.CharField(choices=[("draft", "Draft"), ("in_review", "In Review"), ("approved", "Approved"), ("rejected", "Rejected"), ("archived", "Archived")], default="draft", max_length=50)),
                ("quality_status", models.CharField(choices=[("unknown", "Unknown"), ("low", "Low"), ("acceptable", "Acceptable"), ("high", "High"), ("needs_attention", "Needs Attention")], default="unknown", max_length=50)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("authored_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="authored_item_bank_entries", to=settings.AUTH_USER_MODEL)),
                ("content_concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="item_bank_entries", to="academic.contentconcept")),
            ],
            options={
                "db_table": "item_bank_entry",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ItemOption",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("label", models.CharField(max_length=100)),
                ("content", models.TextField()),
                ("is_correct", models.BooleanField(default=False)),
                ("explanation", models.TextField(blank=True)),
                ("sequence_number", models.PositiveIntegerField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("item_bank_entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="assessments.itembankentry")),
            ],
            options={
                "db_table": "item_option",
                "ordering": ["sequence_number"],
            },
        ),
        migrations.CreateModel(
            name="AssessmentItemBankLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sequence_number", models.PositiveIntegerField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="item_bank_links", to="assessments.assessment")),
                ("item_bank_entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessment_links", to="assessments.itembankentry")),
            ],
            options={
                "db_table": "assessment_item_bank_link",
                "ordering": ["sequence_number"],
            },
        ),
        migrations.AddIndex(
            model_name="itembankentry",
            index=models.Index(fields=["content_concept"], name="item_bank_concept_idx"),
        ),
        migrations.AddIndex(
            model_name="itembankentry",
            index=models.Index(fields=["item_type"], name="item_bank_type_idx"),
        ),
        migrations.AddIndex(
            model_name="itembankentry",
            index=models.Index(fields=["review_status"], name="item_bank_review_idx"),
        ),
        migrations.AddIndex(
            model_name="itembankentry",
            index=models.Index(fields=["quality_status"], name="item_bank_quality_idx"),
        ),
        migrations.AddConstraint(
            model_name="itemoption",
            constraint=models.UniqueConstraint(fields=("item_bank_entry", "sequence_number"), name="unique_item_option_sequence"),
        ),
        migrations.AddConstraint(
            model_name="itemoption",
            constraint=models.CheckConstraint(condition=models.Q(("sequence_number__gte", 1)), name="item_option_sequence_gte_1"),
        ),
        migrations.AddConstraint(
            model_name="assessmentitembanklink",
            constraint=models.UniqueConstraint(fields=("assessment", "sequence_number"), name="unique_assessment_bank_link_sequence"),
        ),
        migrations.AddConstraint(
            model_name="assessmentitembanklink",
            constraint=models.UniqueConstraint(fields=("assessment", "item_bank_entry"), name="unique_assessment_bank_link_item"),
        ),
        migrations.AddConstraint(
            model_name="assessmentitembanklink",
            constraint=models.CheckConstraint(condition=models.Q(("sequence_number__gte", 1)), name="assessment_bank_link_sequence_gte_1"),
        ),
    ]
