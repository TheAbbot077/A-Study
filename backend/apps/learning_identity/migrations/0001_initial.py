import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0004_alter_institution_institution_type_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LearnerLearningProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("ACTIVE", "Active"), ("NEEDS_REVIEW", "Needs review"), ("RESTRICTED", "Restricted"), ("ARCHIVED", "Archived")], default="DRAFT", max_length=24)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("restricted_at", models.DateTimeField(blank=True, null=True)),
                ("restriction_reason", models.CharField(blank=True, max_length=160)),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_identity_profiles", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_identity_profiles", to="users.institution")),
            ],
        ),
        migrations.CreateModel(
            name="LearningProfileVersion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("version_number", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PUBLISHED", "Published"), ("SUPERSEDED", "Superseded"), ("REVOKED", "Revoked")], default="DRAFT", max_length=24)),
                ("summary", models.TextField(blank=True)),
                ("source_revision", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_learning_profile_versions", to=settings.AUTH_USER_MODEL)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="profile_versions", to="learning_identity.learnerlearningprofile")),
                ("published_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="published_learning_profile_versions", to=settings.AUTH_USER_MODEL)),
                ("supersedes_version", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="successor_versions", to="learning_identity.learningprofileversion")),
            ],
            options={"ordering": ["profile_id", "version_number"]},
        ),
        migrations.AddField(
            model_name="learnerlearningprofile",
            name="current_version",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="current_for_profiles", to="learning_identity.learningprofileversion"),
        ),
        migrations.CreateModel(
            name="LearningIdentityAttribute",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("attribute_type", models.CharField(choices=[("PREFERRED_LEARNING_LANGUAGE", "Preferred learning language"), ("TARGET_QUALIFICATION", "Target qualification"), ("TARGET_EXAM_DATE", "Target exam date"), ("WEEKLY_STUDY_CAPACITY", "Weekly study capacity"), ("PRIOR_STUDY_EXPERIENCE", "Prior study experience"), ("ACCESSIBILITY_PREFERENCE", "Accessibility preference"), ("STUDY_GOAL", "Study goal"), ("PREFERRED_EXPLANATION_FORMAT", "Preferred explanation format"), ("PACING_SUPPORT_PREFERENCE", "Pacing support preference")], max_length=64)),
                ("classification", models.CharField(choices=[("DECLARED", "Declared"), ("VERIFIED", "Verified"), ("OBSERVED", "Observed"), ("DERIVED", "Derived")], max_length=16)),
                ("value", models.JSONField()),
                ("value_schema_version", models.PositiveSmallIntegerField(default=1)),
                ("confidence", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ("source_type", models.CharField(choices=[("LEARNER", "Learner"), ("AUTHORIZED_ACTOR", "Authorized actor"), ("INSTITUTION", "Institution"), ("ONBOARDING", "Onboarding"), ("DIAGNOSTIC", "Diagnostic"), ("ASSESSMENT", "Assessment"), ("LEARNING_SESSION", "Learning session"), ("SYSTEM_DERIVATION", "System derivation")], max_length=32)),
                ("source_reference", models.JSONField(blank=True, default=dict)),
                ("declared_at", models.DateTimeField(blank=True, null=True)),
                ("valid_from", models.DateField(blank=True, null=True)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("visibility", models.CharField(choices=[("LEARNER_VISIBLE", "Learner visible"), ("AUTHORIZED_STAFF", "Authorized staff"), ("RESTRICTED", "Restricted"), ("SYSTEM_ONLY", "System only")], default="LEARNER_VISIBLE", max_length=24)),
                ("review_required", models.BooleanField(default=False)),
                ("restricted", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_learning_identity_attributes", to=settings.AUTH_USER_MODEL)),
                ("profile_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attributes", to="learning_identity.learningprofileversion")),
            ],
            options={"ordering": ["profile_version__version_number", "attribute_type", "created_at"]},
        ),
        migrations.CreateModel(
            name="LearningIdentityCommandRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("scope", models.CharField(max_length=80)),
                ("idempotency_key", models.CharField(max_length=128)),
                ("payload_fingerprint", models.CharField(max_length=64)),
                ("result_model", models.CharField(max_length=80)),
                ("result_id", models.UUIDField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddIndex(model_name="learnerlearningprofile", index=models.Index(fields=["tenant", "learner", "status"], name="li_profile_tenant_learner_idx")),
        migrations.AddIndex(model_name="learnerlearningprofile", index=models.Index(fields=["learner", "status"], name="li_profile_learner_status_idx")),
        migrations.AddIndex(model_name="learnerlearningprofile", index=models.Index(fields=["current_version"], name="li_profile_current_idx")),
        migrations.AddConstraint(model_name="learnerlearningprofile", constraint=models.UniqueConstraint(fields=("tenant", "learner"), condition=~Q(status="ARCHIVED"), name="li_one_open_profile_per_learner")),
        migrations.AddConstraint(model_name="learnerlearningprofile", constraint=models.CheckConstraint(condition=Q(status__in=["DRAFT", "ACTIVE", "NEEDS_REVIEW", "RESTRICTED", "ARCHIVED"]), name="li_profile_status_valid")),
        migrations.AddIndex(model_name="learningprofileversion", index=models.Index(fields=["profile", "status", "version_number"], name="li_version_profile_status_idx")),
        migrations.AddIndex(model_name="learningprofileversion", index=models.Index(fields=["published_at"], name="li_version_published_idx")),
        migrations.AddConstraint(model_name="learningprofileversion", constraint=models.UniqueConstraint(fields=("profile", "version_number"), name="li_unique_profile_version_no")),
        migrations.AddConstraint(model_name="learningprofileversion", constraint=models.UniqueConstraint(fields=("profile",), condition=Q(status="DRAFT"), name="li_one_draft_version")),
        migrations.AddConstraint(model_name="learningprofileversion", constraint=models.CheckConstraint(condition=Q(status__in=["DRAFT", "PUBLISHED", "SUPERSEDED", "REVOKED"]), name="li_version_status_valid")),
        migrations.AddConstraint(model_name="learningprofileversion", constraint=models.CheckConstraint(condition=Q(supersedes_version__isnull=True) | ~Q(id=models.F("supersedes_version")), name="li_version_not_self_supersede")),
        migrations.AddIndex(model_name="learningidentityattribute", index=models.Index(fields=["profile_version", "attribute_type"], name="li_attr_version_type_idx")),
        migrations.AddIndex(model_name="learningidentityattribute", index=models.Index(fields=["classification", "visibility"], name="li_attr_class_visibility_idx")),
        migrations.AddIndex(model_name="learningidentityattribute", index=models.Index(fields=["restricted"], name="li_attr_restricted_idx")),
        migrations.AddConstraint(model_name="learningidentityattribute", constraint=models.UniqueConstraint(fields=("profile_version", "attribute_type", "classification"), name="li_unique_attr_type_class")),
        migrations.AddConstraint(model_name="learningidentityattribute", constraint=models.CheckConstraint(condition=Q(attribute_type__in=["PREFERRED_LEARNING_LANGUAGE", "TARGET_QUALIFICATION", "TARGET_EXAM_DATE", "WEEKLY_STUDY_CAPACITY", "PRIOR_STUDY_EXPERIENCE", "ACCESSIBILITY_PREFERENCE", "STUDY_GOAL", "PREFERRED_EXPLANATION_FORMAT", "PACING_SUPPORT_PREFERENCE"]), name="li_attr_type_valid")),
        migrations.AddConstraint(model_name="learningidentityattribute", constraint=models.CheckConstraint(condition=Q(classification__in=["DECLARED", "VERIFIED", "OBSERVED", "DERIVED"]), name="li_attr_class_valid")),
        migrations.AddConstraint(model_name="learningidentityattribute", constraint=models.CheckConstraint(condition=Q(visibility__in=["LEARNER_VISIBLE", "AUTHORIZED_STAFF", "RESTRICTED", "SYSTEM_ONLY"]), name="li_attr_visibility_valid")),
        migrations.AddConstraint(model_name="learningidentityattribute", constraint=models.CheckConstraint(condition=Q(source_type__in=["LEARNER", "AUTHORIZED_ACTOR", "INSTITUTION", "ONBOARDING", "DIAGNOSTIC", "ASSESSMENT", "LEARNING_SESSION", "SYSTEM_DERIVATION"]), name="li_attr_source_valid")),
        migrations.AddConstraint(model_name="learningidentityattribute", constraint=models.CheckConstraint(condition=Q(confidence__isnull=True) | (Q(confidence__gte=0) & Q(confidence__lte=1)), name="li_attr_confidence_bounds")),
        migrations.AddConstraint(model_name="learningidentityattribute", constraint=models.CheckConstraint(condition=Q(valid_from__isnull=True) | Q(valid_until__isnull=True) | Q(valid_until__gte=models.F("valid_from")), name="li_attr_validity_order")),
        migrations.AddConstraint(model_name="learningidentityattribute", constraint=models.CheckConstraint(condition=Q(restricted=False) | Q(visibility__in=["RESTRICTED", "SYSTEM_ONLY"]), name="li_attr_restricted_visibility")),
        migrations.AddIndex(model_name="learningidentitycommandrecord", index=models.Index(fields=["result_model", "result_id"], name="li_command_result_idx")),
        migrations.AddConstraint(model_name="learningidentitycommandrecord", constraint=models.UniqueConstraint(fields=("scope", "idempotency_key"), name="li_command_key_once")),
    ]
