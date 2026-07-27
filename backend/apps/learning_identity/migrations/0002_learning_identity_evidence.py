import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("learning_identity", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningIdentityEvidenceLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_domain", models.CharField(choices=[("IDENTITY", "Identity"), ("SELF_STUDY", "Self-study"), ("ACADEMIC", "Academic"), ("LEARNING", "Learning"), ("ASSESSMENT", "Assessment"), ("DIAGNOSTIC", "Diagnostic"), ("INSTITUTION", "Institution"), ("LEARNING_IDENTITY", "Learning identity")], max_length=32)),
                ("source_type", models.CharField(choices=[("LEARNER_DECLARATION", "Learner declaration"), ("ONBOARDING_CONTEXT", "Onboarding context"), ("INSTITUTIONAL_MEMBERSHIP", "Institutional membership"), ("DIAGNOSTIC_ATTEMPT", "Diagnostic attempt"), ("DIAGNOSTIC_EVIDENCE", "Diagnostic evidence"), ("ASSESSMENT_ATTEMPT", "Assessment attempt"), ("ASSESSMENT_EVIDENCE", "Assessment evidence"), ("MASTERY_EVIDENCE", "Mastery evidence"), ("LEARNING_SESSION", "Learning session"), ("LEARNING_TURN", "Learning turn"), ("PROFILE_CORRECTION", "Profile correction")], max_length=48)),
                ("source_identifier", models.CharField(max_length=128)),
                ("source_revision", models.CharField(blank=True, max_length=80)),
                ("relationship", models.CharField(choices=[("SUPPORTS", "Supports"), ("CONTRADICTS", "Contradicts"), ("CONFIRMS", "Confirms"), ("SUPERSEDES", "Supersedes"), ("CONTEXTUALIZES", "Contextualizes")], max_length=24)),
                ("authority_class", models.CharField(choices=[("DECLARATIVE", "Declarative"), ("INSTITUTIONAL", "Institutional"), ("ASSESSMENT", "Assessment"), ("DIAGNOSTIC", "Diagnostic"), ("OBSERVATIONAL", "Observational"), ("DERIVED", "Derived"), ("SYSTEM", "System")], max_length=24)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("STALE", "Stale"), ("WITHDRAWN", "Withdrawn"), ("INVALIDATED", "Invalidated"), ("SUPERSEDED", "Superseded")], default="ACTIVE", max_length=16)),
                ("source_observed_at", models.DateTimeField(blank=True, null=True)),
                ("valid_from", models.DateField(blank=True, null=True)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("freshness_expires_at", models.DateTimeField(blank=True, null=True)),
                ("weight", models.DecimalField(decimal_places=3, default=1, max_digits=4)),
                ("confidence_contribution", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ("safe_summary", models.CharField(blank=True, max_length=240)),
                ("summary_visibility", models.CharField(choices=[("LEARNER_VISIBLE", "Learner visible"), ("AUTHORIZED_STAFF", "Authorized staff"), ("RESTRICTED", "Restricted"), ("SYSTEM_ONLY", "System only")], default="AUTHORIZED_STAFF", max_length=24)),
                ("metadata_schema_version", models.PositiveSmallIntegerField(default=1)),
                ("linked_at", models.DateTimeField(auto_now_add=True)),
                ("withdrawn_at", models.DateTimeField(blank=True, null=True)),
                ("withdrawal_reason_code", models.CharField(blank=True, max_length=64)),
                ("invalidated_at", models.DateTimeField(blank=True, null=True)),
                ("invalidation_reason_code", models.CharField(blank=True, max_length=64)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
                ("review_required", models.BooleanField(default=False)),
                ("reason_codes", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("attribute", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="evidence_links", to="learning_identity.learningidentityattribute")),
                ("invalidated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="invalidated_learning_identity_evidence", to=settings.AUTH_USER_MODEL)),
                ("linked_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="linked_learning_identity_evidence", to=settings.AUTH_USER_MODEL)),
                ("superseded_by_link", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="supersedes_link", to="learning_identity.learningidentityevidencelink")),
                ("withdrawn_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="withdrawn_learning_identity_evidence", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["attribute_id", "relationship", "source_domain", "source_type", "source_identifier", "source_revision", "created_at"]},
        ),
        migrations.AddIndex(model_name="learningidentityevidencelink", index=models.Index(fields=["attribute"], name="li_ev_attr_idx")),
        migrations.AddIndex(model_name="learningidentityevidencelink", index=models.Index(fields=["attribute", "status"], name="li_ev_attr_status_idx")),
        migrations.AddIndex(model_name="learningidentityevidencelink", index=models.Index(fields=["source_domain", "source_type", "source_identifier"], name="li_ev_source_idx")),
        migrations.AddIndex(model_name="learningidentityevidencelink", index=models.Index(fields=["status"], name="li_ev_status_idx")),
        migrations.AddIndex(model_name="learningidentityevidencelink", index=models.Index(fields=["freshness_expires_at"], name="li_ev_freshness_idx")),
        migrations.AddIndex(model_name="learningidentityevidencelink", index=models.Index(fields=["relationship"], name="li_ev_relationship_idx")),
        migrations.AddIndex(model_name="learningidentityevidencelink", index=models.Index(fields=["authority_class"], name="li_ev_authority_idx")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.UniqueConstraint(fields=("attribute", "source_domain", "source_type", "source_identifier", "relationship", "source_revision"), condition=Q(status="ACTIVE"), name="li_ev_unique_active_source")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(source_domain__in=["IDENTITY", "SELF_STUDY", "ACADEMIC", "LEARNING", "ASSESSMENT", "DIAGNOSTIC", "INSTITUTION", "LEARNING_IDENTITY"]), name="li_ev_domain_valid")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(source_type__in=["LEARNER_DECLARATION", "ONBOARDING_CONTEXT", "INSTITUTIONAL_MEMBERSHIP", "DIAGNOSTIC_ATTEMPT", "DIAGNOSTIC_EVIDENCE", "ASSESSMENT_ATTEMPT", "ASSESSMENT_EVIDENCE", "MASTERY_EVIDENCE", "LEARNING_SESSION", "LEARNING_TURN", "PROFILE_CORRECTION"]), name="li_ev_type_valid")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(relationship__in=["SUPPORTS", "CONTRADICTS", "CONFIRMS", "SUPERSEDES", "CONTEXTUALIZES"]), name="li_ev_relationship_valid")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(authority_class__in=["DECLARATIVE", "INSTITUTIONAL", "ASSESSMENT", "DIAGNOSTIC", "OBSERVATIONAL", "DERIVED", "SYSTEM"]), name="li_ev_authority_valid")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(status__in=["ACTIVE", "STALE", "WITHDRAWN", "INVALIDATED", "SUPERSEDED"]), name="li_ev_status_valid")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(weight__gte=0) & Q(weight__lte=1), name="li_ev_weight_bounds")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(confidence_contribution__isnull=True) | (Q(confidence_contribution__gte=0) & Q(confidence_contribution__lte=1)), name="li_ev_confidence_bounds")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(valid_from__isnull=True) | Q(valid_until__isnull=True) | Q(valid_until__gte=models.F("valid_from")), name="li_ev_validity_order")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(source_observed_at__isnull=True) | Q(freshness_expires_at__isnull=True) | Q(freshness_expires_at__gte=models.F("source_observed_at")), name="li_ev_freshness_order")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(superseded_by_link__isnull=True) | ~Q(id=models.F("superseded_by_link")), name="li_ev_no_self_supersede")),
        migrations.AddConstraint(model_name="learningidentityevidencelink", constraint=models.CheckConstraint(condition=Q(summary_visibility__in=["LEARNER_VISIBLE", "AUTHORIZED_STAFF", "RESTRICTED", "SYSTEM_ONLY"]), name="li_ev_summary_visibility_valid")),
    ]
