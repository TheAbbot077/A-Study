import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0006_content_review_fields"),
        ("content_processing", "0005_teaching_readiness_governance"),
        ("self_study", "0008_teaching_orchestration"),
        ("users", "0004_alter_institution_institution_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SelfStudyWorkspace",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("display_name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("INTENT_REQUIRED", "Intent required"),
                            ("INTENT_IN_PROGRESS", "Intent in progress"),
                            ("MATERIALS_REQUIRED", "Materials required"),
                            ("MATERIALS_PROCESSING", "Materials processing"),
                            ("MATERIALS_BLOCKED", "Materials blocked"),
                            ("MATERIALS_READY", "Materials ready"),
                            ("DIAGNOSTIC_READY", "Diagnostic ready"),
                            ("DIAGNOSTIC_IN_PROGRESS", "Diagnostic in progress"),
                            ("DIAGNOSTIC_COMPLETE", "Diagnostic complete"),
                            ("PLANNING_REQUIRED", "Planning required"),
                            ("PLANNING_IN_PROGRESS", "Planning in progress"),
                            ("PLAN_READY", "Plan ready"),
                            ("PREPARATION_IN_PROGRESS", "Preparation in progress"),
                            ("READY_TO_LEARN", "Ready to learn"),
                            ("LEARNING_ACTIVE", "Learning active"),
                            ("BLOCKED", "Blocked"),
                            ("STALE", "Stale"),
                            ("ARCHIVED", "Archived"),
                        ],
                        default="INTENT_REQUIRED",
                        max_length=32,
                    ),
                ),
                ("idempotency_key", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("active_bridge_plan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="workspaces", to="self_study.bridgeplan")),
                ("active_diagnostic", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="active_for_workspaces", to="self_study.entrydiagnostic")),
                ("active_teaching_preparation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="workspaces", to="self_study.teachingpreparationmanifest")),
                ("active_teaching_session", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="workspaces", to="self_study.selfstudyteachingsession")),
                ("curriculum_resolution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="workspaces", to="self_study.curriculumresolutionattempt")),
                ("intent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="workspaces", to="self_study.selfstudyintent")),
                ("latest_coverage_evaluation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="workspaces", to="self_study.curriculumcoverageevaluation")),
                ("learner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_workspaces", to="users.user")),
                ("published_graph", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="workspaces", to="self_study.curriculumgraphversion")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_workspaces", to="users.institution")),
            ],
            options={
                "db_table": "self_study_workspace",
                "ordering": ["-updated_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["learner", "status"], name="ssi_ws_learner_idx"),
                    models.Index(fields=["tenant", "status"], name="ssi_ws_tenant_idx"),
                    models.Index(fields=["intent"], name="ssi_ws_intent_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("learner", "tenant", "idempotency_key"),
                        condition=~models.Q(idempotency_key=""),
                        name="ssi_ws_idem_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SelfStudyWorkspaceMaterial",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("UPLOADED", "Uploaded"),
                            ("PROCESSING", "Processing"),
                            ("PROCESSED", "Processed"),
                            ("EXTRACTION_FAILED", "Extraction failed"),
                            ("UNSUPPORTED_FORMAT", "Unsupported format"),
                            ("UNLICENSED", "Unlicensed"),
                            ("UNSAFE", "Unsafe"),
                            ("QUARANTINED", "Quarantined"),
                            ("RETIRED", "Retired"),
                            ("STALE", "Stale"),
                            ("ELIGIBLE", "Eligible"),
                            ("INELIGIBLE", "Ineligible"),
                        ],
                        default="UPLOADED",
                        max_length=32,
                    ),
                ),
                ("blocker_codes", models.JSONField(blank=True, default=list)),
                ("safe_status_summary", models.JSONField(blank=True, default=dict)),
                ("idempotency_key", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("retired_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("attached_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attached_self_study_materials", to="users.user")),
                ("content_processing_job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="self_study_workspace_links", to="content_processing.contentprocessingjob")),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="self_study_workspace_links", to="academic.learningresource")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="materials", to="self_study.selfstudyworkspace")),
            ],
            options={
                "db_table": "self_study_workspace_material",
                "ordering": ["created_at", "resource_id"],
                "indexes": [
                    models.Index(fields=["workspace", "status"], name="ssi_wsm_status_idx"),
                    models.Index(fields=["resource"], name="ssi_wsm_resource_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("workspace", "resource"), name="ssi_wsm_resource_unique"),
                    models.UniqueConstraint(
                        fields=("workspace", "idempotency_key"),
                        condition=~models.Q(idempotency_key=""),
                        name="ssi_wsm_idem_unique",
                    ),
                ],
            },
        ),
    ]
