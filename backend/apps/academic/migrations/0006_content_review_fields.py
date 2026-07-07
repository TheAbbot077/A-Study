import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0005_resource_ingestion"),
        ("users", "0004_alter_institution_institution_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentsection",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("in_review", "In Review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("archived", "Archived"),
                ],
                default="draft",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="contentsection",
            name="quality_status",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("low", "Low"),
                    ("acceptable", "Acceptable"),
                    ("high", "High"),
                    ("needs_attention", "Needs Attention"),
                ],
                default="unknown",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="contentsection",
            name="review_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="contentsection",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contentsection",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approved_content_sections",
                to="users.user",
            ),
        ),
        migrations.AddField(
            model_name="contentconcept",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("in_review", "In Review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("archived", "Archived"),
                ],
                default="draft",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="contentconcept",
            name="quality_status",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("low", "Low"),
                    ("acceptable", "Acceptable"),
                    ("high", "High"),
                    ("needs_attention", "Needs Attention"),
                ],
                default="unknown",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="contentconcept",
            name="review_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="contentconcept",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contentconcept",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approved_content_concepts",
                to="users.user",
            ),
        ),
    ]
