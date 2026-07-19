import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("content_processing", "0004_academic_proposals_and_population"),
    ]

    operations = [
        migrations.CreateModel(name="ProposalReviewSession", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("proposal_version", models.CharField(max_length=64)), ("proposal_checksum", models.CharField(max_length=128)),
            ("status", models.CharField(choices=[("not_started", "Not started"), ("in_progress", "In progress"), ("ready_for_approval", "Ready for approval"), ("approved", "Approved"), ("approved_with_edits", "Approved with edits"), ("rejected", "Rejected"), ("reprocess_requested", "Reprocessing requested"), ("superseded", "Superseded"), ("abandoned", "Abandoned")], default="not_started", max_length=32)),
            ("submitted_at", models.DateTimeField(blank=True, null=True)), ("closed_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("opened_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="opened_academic_reviews", to=settings.AUTH_USER_MODEL)),
            ("reviewer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="academic_reviews", to=settings.AUTH_USER_MODEL)),
            ("proposal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_review_sessions", to="content_processing.academicimportproposal")),
        ], options={"db_table": "academic_review_session", "ordering": ["-created_at"]}),
        migrations.CreateModel(name="ProposalItemDecision", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("item_type", models.CharField(choices=[("section", "Section"), ("concept", "Concept")], max_length=16)),
            ("decision", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("edited", "Edited"), ("moved", "Moved")], default="pending", max_length=16)),
            ("reason", models.TextField(blank=True)), ("decided_at", models.DateTimeField(blank=True, null=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("decided_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="academic_item_decisions", to=settings.AUTH_USER_MODEL)),
            ("proposed_concept", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="review_decisions", to="content_processing.proposedconcept")),
            ("proposed_section", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="review_decisions", to="content_processing.proposedsection")),
            ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="item_decisions", to="academic_review.proposalreviewsession")),
        ], options={"db_table": "academic_review_item_decision"}),
        migrations.AddConstraint(model_name="proposalitemdecision", constraint=models.UniqueConstraint(fields=("session", "item_type", "proposed_section", "proposed_concept"), name="ar_item_decision_unique")),
        migrations.CreateModel(name="ProposalItemEdit", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("title", models.CharField(blank=True, max_length=255)),
            ("ordering", models.PositiveIntegerField(blank=True, null=True)), ("reason", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("decision", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="edit", to="academic_review.proposalitemdecision")),
            ("edited_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_item_edits", to=settings.AUTH_USER_MODEL)),
            ("parent_section", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="review_parent_edits", to="content_processing.proposedsection")),
            ("target_section", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="review_concept_moves", to="content_processing.proposedsection")),
        ], options={"db_table": "academic_review_item_edit"}),
        migrations.CreateModel(name="ProposalBulkDecision", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("policy_code", models.CharField(max_length=64)), ("policy_version", models.CharField(max_length=64)),
            ("affected_count", models.PositiveIntegerField()), ("preview", models.JSONField(default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("applied_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_bulk_decisions", to=settings.AUTH_USER_MODEL)),
            ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bulk_decisions", to="academic_review.proposalreviewsession")),
        ], options={"db_table": "academic_review_bulk_decision"}),
        migrations.CreateModel(name="ProposalOverride", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("reason", models.TextField()), ("policy_version", models.CharField(max_length=64)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("overridden_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_review_overrides", to=settings.AUTH_USER_MODEL)),
            ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="overrides", to="academic_review.proposalreviewsession")),
            ("validation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_review_overrides", to="content_processing.proposalvalidation")),
        ], options={"db_table": "academic_review_override"}),
        migrations.AddConstraint(model_name="proposaloverride", constraint=models.UniqueConstraint(fields=("session", "validation"), name="ar_override_unique")),
        migrations.CreateModel(name="ProposalFindingResolution", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("resolution_type", models.CharField(choices=[("rejection", "Resolved by rejection"), ("edit", "Resolved by edit"), ("move", "Resolved by move"), ("override", "Resolved by override")], max_length=16)),
            ("note", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("item_decision", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="finding_resolutions", to="academic_review.proposalitemdecision")),
            ("override", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="resolution", to="academic_review.proposaloverride")),
            ("resolved_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_finding_resolutions", to=settings.AUTH_USER_MODEL)),
            ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="finding_resolutions", to="academic_review.proposalreviewsession")),
            ("validation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_review_resolutions", to="content_processing.proposalvalidation")),
        ], options={"db_table": "academic_review_finding_resolution"}),
        migrations.AddConstraint(model_name="proposalfindingresolution", constraint=models.UniqueConstraint(fields=("session", "validation"), name="ar_finding_resolution_unique")),
        migrations.CreateModel(name="ApprovedProposalProjection", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("proposal_checksum", models.CharField(max_length=128)),
            ("projection_version", models.CharField(max_length=64)), ("checksum", models.CharField(max_length=128)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_academic_projections", to=settings.AUTH_USER_MODEL)),
            ("proposal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approved_review_projections", to="content_processing.academicimportproposal")),
            ("session", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_projection", to="academic_review.proposalreviewsession")),
        ], options={"db_table": "academic_review_approved_projection"}),
        migrations.CreateModel(name="ApprovedSection", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("title", models.CharField(max_length=255)), ("ordering", models.PositiveIntegerField()),
            ("parent_source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_child_projection_items", to="content_processing.proposedsection")),
            ("projection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="academic_review.approvedproposalprojection")),
            ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approved_projection_items", to="content_processing.proposedsection")),
        ], options={"db_table": "academic_review_approved_section", "ordering": ["ordering"]}),
        migrations.AddConstraint(model_name="approvedsection", constraint=models.UniqueConstraint(fields=("projection", "ordering"), name="ar_approved_section_order_unique")),
        migrations.CreateModel(name="ApprovedConcept", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("title", models.CharField(max_length=255)), ("ordering", models.PositiveIntegerField()),
            ("supporting_text", models.TextField()), ("explanation", models.TextField()),
            ("projection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concepts", to="academic_review.approvedproposalprojection")),
            ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concepts", to="academic_review.approvedsection")),
            ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approved_projection_items", to="content_processing.proposedconcept")),
        ], options={"db_table": "academic_review_approved_concept", "ordering": ["section_id", "ordering"]}),
        migrations.AddConstraint(model_name="approvedconcept", constraint=models.UniqueConstraint(fields=("section", "ordering"), name="ar_approved_concept_order_unique")),
    ]
