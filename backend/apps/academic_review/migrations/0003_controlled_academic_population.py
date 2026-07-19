import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academic_review", "0002_reviewed_approval_projection"),
        ("academic", "0006_content_review_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="approvedproposalprojection", name="status",
            field=models.CharField(choices=[("created", "Created"), ("ready_for_population", "Ready for population"), ("populating", "Populating"), ("superseded", "Superseded"), ("populated", "Populated")], default="created", max_length=32),
        ),
        migrations.CreateModel(
            name="AcademicPopulationRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("idempotency_key", models.CharField(max_length=128, unique=True)),
                ("request_fingerprint", models.CharField(max_length=128)),
                ("projection_fingerprint", models.CharField(max_length=128)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("populating", "Populating"), ("populated", "Populated"), ("failed", "Failed")], default="planned", max_length=16)),
                ("plan_snapshot", models.JSONField(default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("failure_message", models.CharField(blank=True, max_length=500)),
                ("created_section_count", models.PositiveIntegerField(default=0)),
                ("matched_section_count", models.PositiveIntegerField(default=0)),
                ("created_concept_count", models.PositiveIntegerField(default=0)),
                ("matched_concept_count", models.PositiveIntegerField(default=0)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approval_decision", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="population_runs", to="academic_review.approvaldecision")),
                ("approved_projection", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="population_runs", to="academic_review.approvedproposalprojection")),
                ("prior_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="retries", to="academic_review.academicpopulationrun")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_population_runs", to=settings.AUTH_USER_MODEL)),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_population_runs", to="academic.learningresource")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academic_population_runs", to="academic.subject")),
            ],
            options={"db_table": "academic_review_population_run", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint("academicpopulationrun", models.UniqueConstraint(condition=models.Q(("status", "populated")), fields=("approved_projection",), name="ar_one_populated_run_per_projection")),
        migrations.AddIndex("academicpopulationrun", models.Index(fields=["approved_projection", "status"], name="ar_pop_projection_status")),
        migrations.AddIndex("academicpopulationrun", models.Index(fields=["resource", "subject"], name="ar_pop_resource_subject")),
        migrations.AddIndex("academicpopulationrun", models.Index(fields=["requested_by", "created_at"], name="ar_pop_actor_created")),
        migrations.CreateModel(
            name="SectionPopulationMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("academic_section_id", models.UUIDField()), ("stable_source_key", models.CharField(max_length=160)),
                ("outcome", models.CharField(choices=[("created", "Created"), ("matched", "Matched")], max_length=16)),
                ("sequence_number", models.PositiveIntegerField()), ("populated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("approved_section", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="population_mappings", to="academic_review.approvedsection")),
                ("population_run", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="section_mappings", to="academic_review.academicpopulationrun")),
            ], options={"db_table": "academic_review_section_population_mapping"},
        ),
        migrations.AddConstraint("sectionpopulationmapping", models.UniqueConstraint(fields=("population_run", "approved_section"), name="ar_pop_section_item_unique")),
        migrations.AddConstraint("sectionpopulationmapping", models.UniqueConstraint(fields=("population_run", "stable_source_key"), name="ar_pop_section_key_unique")),
        migrations.AddIndex("sectionpopulationmapping", models.Index(fields=["approved_section", "academic_section_id"], name="ar_pop_section_provenance")),
        migrations.CreateModel(
            name="ConceptPopulationMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("academic_concept_id", models.UUIDField()), ("academic_section_id", models.UUIDField()),
                ("stable_source_key", models.CharField(max_length=160)),
                ("outcome", models.CharField(choices=[("created", "Created"), ("matched", "Matched")], max_length=16)),
                ("sequence_number", models.PositiveIntegerField()), ("populated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("approved_concept", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="population_mappings", to="academic_review.approvedconcept")),
                ("population_run", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="concept_mappings", to="academic_review.academicpopulationrun")),
            ], options={"db_table": "academic_review_concept_population_mapping"},
        ),
        migrations.AddConstraint("conceptpopulationmapping", models.UniqueConstraint(fields=("population_run", "approved_concept"), name="ar_pop_concept_item_unique")),
        migrations.AddConstraint("conceptpopulationmapping", models.UniqueConstraint(fields=("population_run", "stable_source_key"), name="ar_pop_concept_key_unique")),
        migrations.AddIndex("conceptpopulationmapping", models.Index(fields=["approved_concept", "academic_concept_id"], name="ar_pop_concept_provenance")),
    ]
