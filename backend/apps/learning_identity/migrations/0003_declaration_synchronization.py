import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("learning_identity", "0002_learning_identity_evidence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningIdentityDeclarationSynchronization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("onboarding_session_id", models.UUIDField()),
                ("onboarding_revision", models.PositiveIntegerField()),
                ("source_event_id", models.CharField(blank=True, max_length=128)),
                ("payload_fingerprint", models.CharField(max_length=64)),
                ("source_schema_version", models.PositiveSmallIntegerField(default=1)),
                ("status", models.CharField(choices=[("APPLIED", "Applied"), ("NO_CHANGE", "No change"), ("BLOCKED", "Blocked"), ("FAILED", "Failed")], max_length=16)),
                (
                    "result_code",
                    models.CharField(
                        choices=[
                            ("APPLIED", "Applied"),
                            ("NO_CHANGE", "No change"),
                            ("BLOCKED", "Blocked"),
                            ("FAILED", "Failed"),
                            ("ONBOARDING_REVISION_STALE", "Onboarding revision stale"),
                            ("ONBOARDING_REVISION_ALREADY_APPLIED", "Onboarding revision already applied"),
                            ("ONBOARDING_REVISION_PAYLOAD_CONFLICT", "Onboarding revision payload conflict"),
                            ("ONBOARDING_REVISION_UNAVAILABLE", "Onboarding revision unavailable"),
                            ("ONBOARDING_SOURCE_NOT_FOUND", "Onboarding source not found"),
                            ("ONBOARDING_NOT_COMPLETED", "Onboarding not completed"),
                            ("TENANT_MISMATCH", "Tenant mismatch"),
                            ("LEARNER_MISMATCH", "Learner mismatch"),
                            ("UNRELATED_DRAFT_EXISTS", "Unrelated draft exists"),
                            ("PROFILE_VERSION_CONFLICT", "Profile version conflict"),
                            ("PROVENANCE_BLOCKED", "Provenance blocked"),
                            ("PROVENANCE_REVIEW_REQUIRED", "Provenance review required"),
                        ],
                        max_length=64,
                    ),
                ),
                ("readiness_status", models.CharField(blank=True, max_length=24)),
                ("change_counts", models.JSONField(blank=True, default=dict)),
                ("reason_codes", models.JSONField(blank=True, default=list)),
                ("idempotency_key", models.CharField(blank=True, max_length=128)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("blocked_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_identity_declaration_synchronizations", to=settings.AUTH_USER_MODEL)),
                ("profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="declaration_synchronizations", to="learning_identity.learnerlearningprofile")),
                ("profile_version", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="declaration_synchronizations", to="learning_identity.learningprofileversion")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="learning_identity_declaration_synchronizations", to="users.institution")),
            ],
            options={
                "ordering": ["-created_at", "onboarding_session_id", "onboarding_revision"],
            },
        ),
        migrations.AddIndex(model_name="learningidentitydeclarationsynchronization", index=models.Index(fields=["tenant", "learner"], name="li_declsync_tenant_learner_idx")),
        migrations.AddIndex(model_name="learningidentitydeclarationsynchronization", index=models.Index(fields=["profile"], name="li_declsync_profile_idx")),
        migrations.AddIndex(model_name="learningidentitydeclarationsynchronization", index=models.Index(fields=["onboarding_session_id", "onboarding_revision"], name="li_declsync_source_rev_idx")),
        migrations.AddIndex(model_name="learningidentitydeclarationsynchronization", index=models.Index(fields=["source_event_id"], name="li_declsync_event_idx")),
        migrations.AddIndex(model_name="learningidentitydeclarationsynchronization", index=models.Index(fields=["status"], name="li_declsync_status_idx")),
        migrations.AddIndex(model_name="learningidentitydeclarationsynchronization", index=models.Index(fields=["applied_at"], name="li_declsync_applied_idx")),
        migrations.AddIndex(model_name="learningidentitydeclarationsynchronization", index=models.Index(fields=["profile", "onboarding_session_id"], name="li_declsync_profile_source_idx")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.UniqueConstraint(fields=("onboarding_session_id", "onboarding_revision"), name="li_declsync_unique_source_rev")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.UniqueConstraint(fields=("source_event_id",), condition=~Q(source_event_id=""), name="li_declsync_unique_event")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.UniqueConstraint(fields=("idempotency_key",), condition=~Q(idempotency_key=""), name="li_declsync_unique_idem")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.CheckConstraint(condition=Q(onboarding_revision__gt=0), name="li_declsync_revision_positive")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.CheckConstraint(condition=Q(status__in=["APPLIED", "NO_CHANGE", "BLOCKED", "FAILED"]), name="li_declsync_status_valid")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.CheckConstraint(condition=Q(result_code__in=["APPLIED", "NO_CHANGE", "BLOCKED", "FAILED", "ONBOARDING_REVISION_STALE", "ONBOARDING_REVISION_ALREADY_APPLIED", "ONBOARDING_REVISION_PAYLOAD_CONFLICT", "ONBOARDING_REVISION_UNAVAILABLE", "ONBOARDING_SOURCE_NOT_FOUND", "ONBOARDING_NOT_COMPLETED", "TENANT_MISMATCH", "LEARNER_MISMATCH", "UNRELATED_DRAFT_EXISTS", "PROFILE_VERSION_CONFLICT", "PROVENANCE_BLOCKED", "PROVENANCE_REVIEW_REQUIRED"]), name="li_declsync_result_valid")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.CheckConstraint(condition=Q(payload_fingerprint__regex="^[0-9a-f]{64}$"), name="li_declsync_fp_valid")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.CheckConstraint(condition=Q(status="APPLIED", applied_at__isnull=False) | ~Q(status="APPLIED"), name="li_declsync_applied_at")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.CheckConstraint(condition=Q(status="BLOCKED", blocked_at__isnull=False) | ~Q(status="BLOCKED"), name="li_declsync_blocked_at")),
        migrations.AddConstraint(model_name="learningidentitydeclarationsynchronization", constraint=models.CheckConstraint(condition=Q(status="FAILED", failed_at__isnull=False) | ~Q(status="FAILED"), name="li_declsync_failed_at")),
    ]
