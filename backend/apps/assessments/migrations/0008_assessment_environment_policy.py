import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0007_assessment_experience"),
        ("academic", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssessmentEnvironmentPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=96)),
                ("version", models.CharField(max_length=64)),
                ("purpose", models.CharField(choices=[("entry_diagnostic", "Entry Diagnostic"), ("prerequisite_check", "Prerequisite Check"), ("concept_check", "Concept Check"), ("formative", "Formative"), ("practice", "Practice"), ("summative", "Summative"), ("remediation_check", "Remediation Check")], max_length=50)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("retired", "Retired"), ("superseded", "Superseded")], default="draft", max_length=16)),
                ("effective_from", models.DateTimeField()),
                ("effective_to", models.DateTimeField(blank=True, null=True)),
                ("checksum", models.CharField(default="", max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("retired_at", models.DateTimeField(blank=True, null=True)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "assessment_environment_policy",
            },
        ),
        migrations.CreateModel(
            name="AssessmentEnvironmentRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("capability_code", models.CharField(max_length=96)),
                ("disposition", models.CharField(choices=[("ALLOWED", "Allowed"), ("PROHIBITED", "Prohibited"), ("RESTRICTED", "Restricted"), ("REQUIRED", "Required")], max_length=16)),
                ("restriction_type", models.CharField(blank=True, default="", max_length=64)),
                ("restriction_config", models.JSONField(blank=True, default=dict)),
                ("reason_code", models.CharField(blank=True, default="", max_length=96)),
                ("priority", models.PositiveIntegerField(default=0)),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rules", to="assessments.assessmentenvironmentpolicy")),
            ],
            options={
                "db_table": "assessment_environment_rule",
            },
        ),
        migrations.AddField(
            model_name="assessmentexperience",
            name="environment_policy",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assessment_experiences", to="assessments.assessmentenvironmentpolicy"),
        ),
        migrations.AddField(
            model_name="assessmentexperience",
            name="environment_policy_checksum",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="assessmentexperience",
            name="environment_policy_version",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddConstraint(
            model_name="assessmentenvironmentpolicy",
            constraint=models.UniqueConstraint(fields=("code", "version"), name="assessment_env_policy_code_version_unique"),
        ),
        migrations.AddIndex(
            model_name="assessmentenvironmentpolicy",
            index=models.Index(fields=["purpose", "status"], name="assess_env_policy_purpose_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="assessmentenvironmentrule",
            constraint=models.UniqueConstraint(fields=("policy", "capability_code"), name="assessment_env_rule_policy_capability_unique"),
        ),
        migrations.AddIndex(
            model_name="assessmentenvironmentrule",
            index=models.Index(fields=["policy", "priority"], name="assess_env_rule_policy_priority_idx"),
        ),
    ]
