import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


def assign_legacy_approval_versions(apps, schema_editor):
    projection_model = apps.get_model("academic_review", "ApprovedProposalProjection")
    for projection in projection_model.objects.filter(approval_version="legacy").iterator():
        projection_model.objects.filter(pk=projection.pk).update(approval_version=f"legacy:{projection.pk}")


class Migration(migrations.Migration):
    dependencies = [
        ("academic_review", "0001_initial"),
        ("academic", "0006_content_review_fields"),
        ("users", "0004_alter_institution_institution_type_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField("proposalreviewsession", "version", models.PositiveIntegerField(default=1)),
        migrations.CreateModel(name="ApprovalReadinessSnapshot", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("proposal_version", models.CharField(max_length=64)), ("proposal_checksum", models.CharField(max_length=128)),
            ("review_session_version", models.PositiveIntegerField()), ("ready", models.BooleanField(default=False)),
            ("pending_sections", models.PositiveIntegerField(default=0)), ("pending_concepts", models.PositiveIntegerField(default=0)),
            ("accepted_sections", models.PositiveIntegerField(default=0)), ("accepted_concepts", models.PositiveIntegerField(default=0)),
            ("rejected_sections", models.PositiveIntegerField(default=0)), ("rejected_concepts", models.PositiveIntegerField(default=0)),
            ("blocking_findings", models.PositiveIntegerField(default=0)), ("resolved_findings", models.PositiveIntegerField(default=0)),
            ("orphan_concepts", models.PositiveIntegerField(default=0)), ("invalid_hierarchy", models.PositiveIntegerField(default=0)),
            ("duplicate_titles", models.PositiveIntegerField(default=0)), ("override_count", models.PositiveIntegerField(default=0)),
            ("policy_version", models.CharField(max_length=64)), ("reasons", models.JSONField(default=list)), ("checksum", models.CharField(max_length=128)),
            ("evaluated_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("evaluated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_readiness_evaluations", to=settings.AUTH_USER_MODEL)),
            ("proposal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approval_readiness_snapshots", to="content_processing.academicimportproposal")),
            ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="readiness_snapshots", to="academic_review.proposalreviewsession")),
        ], options={"db_table": "academic_review_readiness_snapshot", "ordering": ["-evaluated_at"]}),
        migrations.AddConstraint("approvalreadinesssnapshot", models.UniqueConstraint(fields=("session", "review_session_version", "checksum"), name="ar_readiness_snapshot_unique")),
        migrations.CreateModel(name="ApprovalDecision", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("decision", models.CharField(choices=[("approved", "Approved"), ("approved_with_edits", "Approved with edits"), ("rejected", "Rejected")], max_length=32)),
            ("approval_version", models.CharField(max_length=128)), ("idempotency_key", models.CharField(max_length=128)), ("reason", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("decided_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="review_approval_decisions", to=settings.AUTH_USER_MODEL)),
            ("proposal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="review_approval_decisions", to="content_processing.academicimportproposal")),
            ("readiness_snapshot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approval_decisions", to="academic_review.approvalreadinesssnapshot")),
            ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approval_decisions", to="academic_review.proposalreviewsession")),
        ], options={"db_table": "academic_review_approval_decision"}),
        migrations.AddConstraint("approvaldecision", models.UniqueConstraint(fields=("session", "idempotency_key"), name="ar_approval_idempotency_unique")),
        migrations.AddConstraint("approvaldecision", models.UniqueConstraint(fields=("session", "approval_version"), name="ar_approval_version_unique")),
        migrations.AddField("approvedproposalprojection", "approval_decision", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="projection", to="academic_review.approvaldecision")),
        migrations.AddField("approvedproposalprojection", "approval_version", models.CharField(default="legacy", max_length=128), preserve_default=False),
        migrations.AddField("approvedproposalprojection", "resource", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_proposal_projections", to="academic.learningresource")),
        migrations.AddField("approvedproposalprojection", "subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_proposal_projections", to="academic.subject")),
        migrations.AddField("approvedproposalprojection", "institution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_proposal_projections", to="users.institution")),
        migrations.AddField("approvedproposalprojection", "status", models.CharField(choices=[("created", "Created"), ("ready_for_population", "Ready for population"), ("superseded", "Superseded"), ("populated", "Populated")], default="created", max_length=32)),
        migrations.AddField("approvedproposalprojection", "hierarchy_checksum", models.CharField(blank=True, max_length=128)),
        migrations.AddField("approvedproposalprojection", "concepts_checksum", models.CharField(blank=True, max_length=128)),
        migrations.AddField("approvedproposalprojection", "provenance_checksum", models.CharField(blank=True, max_length=128)),
        migrations.RunPython(assign_legacy_approval_versions, migrations.RunPython.noop),
        migrations.AddConstraint("approvedproposalprojection", models.UniqueConstraint(fields=("proposal", "approval_version"), name="ar_projection_approval_version_unique")),
        migrations.AddField("approvedsection", "canonical_title", models.CharField(default="", max_length=255)),
        migrations.AddField("approvedsection", "depth", models.PositiveIntegerField(default=1)),
        migrations.AddField("approvedsection", "parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="academic_review.approvedsection")),
        migrations.AddField("approvedsection", "page_range", models.JSONField(default=dict)),
        migrations.AddField("approvedsection", "evidence_references", models.JSONField(default=list)),
        migrations.AddField("approvedsection", "review_decision", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_section_projections", to="academic_review.proposalitemdecision")),
        migrations.AddField("approvedsection", "edit_reference", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_section_projections", to="academic_review.proposalitemedit")),
        migrations.AddField("approvedsection", "override_references", models.JSONField(default=list)),
        migrations.AddField("approvedconcept", "canonical_title", models.CharField(default="", max_length=255)),
        migrations.AddField("approvedconcept", "page_range", models.JSONField(default=dict)),
        migrations.AddField("approvedconcept", "supporting_evidence", models.JSONField(default=list)),
        migrations.AddField("approvedconcept", "review_decision", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_concept_projections", to="academic_review.proposalitemdecision")),
        migrations.AddField("approvedconcept", "edit_reference", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_concept_projections", to="academic_review.proposalitemedit")),
        migrations.AddField("approvedconcept", "override_references", models.JSONField(default=list)),
    ]
