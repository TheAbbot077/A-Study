import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("self_study", "0005_contentevidenceunit_evidencemappingrun_and_more"),
        ("users", "0004_alter_institution_institution_type_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BridgePlanningRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("target_manifest", models.JSONField()), ("input_manifest", models.JSONField()),
                ("algorithm_version", models.CharField(max_length=64)), ("policy_version", models.CharField(max_length=64)),
                ("approval_policy_version", models.CharField(max_length=64)), ("applicability_version", models.CharField(max_length=64)),
                ("run_fingerprint", models.CharField(max_length=128)),
                ("status", models.CharField(choices=[("PENDING","Pending"),("PLANNING","Planning"),("PLAN_READY","Plan ready"),("FAILED","Failed"),("STALE","Stale"),("INVALIDATED","Invalidated"),("SUPERSEDED","Superseded")], default="PENDING", max_length=16)),
                ("stage", models.CharField(default="CREATED", max_length=32)), ("claim_token", models.UUIDField(blank=True, null=True)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)), ("claimed_by", models.CharField(blank=True, max_length=128)),
                ("failure_code", models.CharField(blank=True, max_length=96)), ("failure_detail", models.CharField(blank=True, max_length=500)),
                ("version", models.PositiveIntegerField(default=1)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)), ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("coverage_evaluation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bridge_planning_runs", to="self_study.curriculumcoverageevaluation")),
                ("diagnostic_profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bridge_planning_runs", to="self_study.diagnosticplacementprofile")),
                ("graph_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bridge_planning_runs", to="self_study.curriculumgraphversion")),
                ("intent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bridge_planning_runs", to="self_study.selfstudyintent")),
                ("predecessor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="successors", to="self_study.bridgeplanningrun")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requested_bridge_planning_runs", to=settings.AUTH_USER_MODEL)),
                ("selection_decision", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bridge_planning_runs", to="self_study.curriculumselectiondecision")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bridge_planning_runs", to="users.institution")),
            ],
            options={"db_table":"self_study_bridge_planning_run", "indexes":[models.Index(fields=["intent","status"], name="ssi_bridge_run_status_idx"),models.Index(fields=["graph_version","status"], name="ssi_bridge_run_graph_idx")], "constraints":[models.UniqueConstraint(condition=models.Q(("status__in",["INVALIDATED","SUPERSEDED"]), _negated=True), fields=("tenant","run_fingerprint"), name="ssi_bridge_run_fp_unique")]},
        ),
        migrations.CreateModel(
            name="BridgePlan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("target_set_snapshot", models.JSONField()), ("target_set_fingerprint", models.CharField(max_length=128)),
                ("node_set_fingerprint", models.CharField(max_length=128)), ("dependency_set_fingerprint", models.CharField(max_length=128)),
                ("blocker_set_fingerprint", models.CharField(max_length=128)), ("plan_fingerprint", models.CharField(max_length=128)),
                ("algorithm_version", models.CharField(max_length=64)), ("policy_version", models.CharField(max_length=64)),
                ("status", models.CharField(choices=[("PROPOSED","Proposed"),("READY_FOR_REVIEW","Ready for review"),("APPROVED","Approved"),("ACTIVE","Active"),("BLOCKED","Blocked"),("REJECTED","Rejected"),("STALE","Stale"),("INVALIDATED","Invalidated"),("SUPERSEDED","Superseded")], default="PROPOSED", max_length=24)),
                ("generated_at", models.DateTimeField(auto_now_add=True)), ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("approval_reason", models.TextField(blank=True)), ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)), ("rejection_reason", models.TextField(blank=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("activated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="activated_bridge_plans", to=settings.AUTH_USER_MODEL)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_bridge_plans", to=settings.AUTH_USER_MODEL)),
                ("graph_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bridge_plans", to="self_study.curriculumgraphversion")),
                ("intent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bridge_plans", to="self_study.selfstudyintent")),
                ("predecessor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="successors", to="self_study.bridgeplan")),
                ("rejected_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="rejected_bridge_plans", to=settings.AUTH_USER_MODEL)),
                ("run", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="plan", to="self_study.bridgeplanningrun")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bridge_plans", to="users.institution")),
            ],
            options={"db_table":"self_study_bridge_plan", "indexes":[models.Index(fields=["intent","status"], name="ssi_bridge_plan_status_idx")], "constraints":[models.UniqueConstraint(fields=("tenant","plan_fingerprint"), name="ssi_bridge_plan_fp_unique"),models.UniqueConstraint(condition=models.Q(("status","ACTIVE")), fields=("tenant","intent","target_set_fingerprint"), name="ssi_bridge_one_active_scope")]},
        ),
        migrations.CreateModel(
            name="BridgePlanNode",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("node_type", models.CharField(max_length=32)), ("ordinal", models.PositiveIntegerField()), ("topological_layer", models.PositiveIntegerField()),
                ("learner_disposition", models.CharField(choices=[("ENTRY","Entry"),("PREREQUISITE_REQUIRED","Prerequisite required"),("TARGET_REQUIRED","Target required"),("REINFORCEMENT","Reinforcement"),("DIAGNOSTIC_REVIEW","Diagnostic review"),("DEFERRED","Deferred"),("NOT_APPLICABLE","Not applicable")], max_length=32)),
                ("requirement_type", models.CharField(choices=[("MANDATORY","Mandatory"),("CONDITIONAL","Conditional"),("OPTIONAL","Optional"),("REINFORCEMENT_ONLY","Reinforcement only")], max_length=24)),
                ("inclusion_rationale", models.JSONField(default=list)), ("placement_band", models.CharField(max_length=32)),
                ("coverage_state", models.CharField(max_length=16)),
                ("material_feasibility", models.CharField(choices=[("FEASIBLE","Feasible"),("PARTIALLY_FEASIBLE","Partially feasible"),("MATERIAL_MISSING","Material missing"),("MATERIAL_CONFLICTING","Material conflicting"),("EVIDENCE_STALE","Evidence stale"),("POLICY_BLOCKED","Policy blocked"),("NOT_APPLICABLE","Not applicable")], max_length=24)),
                ("is_target", models.BooleanField(default=False)), ("is_entry", models.BooleanField(default=False)), ("is_required", models.BooleanField(default=True)),
                ("blocker_count", models.PositiveIntegerField(default=0)), ("dependency_count", models.PositiveIntegerField(default=0)),
                ("coverage_citations", models.JSONField(default=list)), ("fingerprint", models.CharField(max_length=128)),
                ("coverage", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bridge_plan_nodes", to="self_study.curriculumnodecoverage")),
                ("graph_node", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bridge_plan_nodes", to="self_study.curriculumnode")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="nodes", to="self_study.bridgeplan")),
            ],
            options={"db_table":"self_study_bridge_plan_node", "indexes":[models.Index(fields=["plan","topological_layer","ordinal"], name="ssi_bridge_node_order_idx")], "constraints":[models.UniqueConstraint(fields=("plan","graph_node"), name="ssi_bridge_plan_node_unique"),models.UniqueConstraint(fields=("plan","fingerprint"), name="ssi_bridge_node_fp_unique")]},
        ),
        migrations.CreateModel(
            name="BridgePlanFinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=96)), ("severity", models.CharField(choices=[("INFO","Info"),("WARNING","Warning"),("BLOCKER","Blocker")], max_length=16)),
                ("blocking", models.BooleanField(default=False)), ("scope", models.CharField(max_length=32)),
                ("affected_identities", models.JSONField(default=list)), ("details", models.JSONField(default=dict)),
                ("algorithm_version", models.CharField(max_length=64)), ("policy_version", models.CharField(max_length=64)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="findings", to="self_study.bridgeplan")),
            ],
            options={"db_table":"self_study_bridge_plan_finding", "indexes":[models.Index(fields=["plan","blocking","severity"], name="ssi_bridge_finding_idx")]},
        ),
        migrations.CreateModel(
            name="BridgePlanDependency",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("edge_type", models.CharField(max_length=24)),
                ("requirement_type", models.CharField(choices=[("MANDATORY","Mandatory"),("CONDITIONAL","Conditional"),("OPTIONAL","Optional"),("REINFORCEMENT_ONLY","Reinforcement only")], max_length=24)),
                ("affects_ordering", models.BooleanField(default=True)), ("rationale", models.JSONField(default=list)), ("fingerprint", models.CharField(max_length=128)),
                ("graph_edge", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bridge_dependencies", to="self_study.curriculumedge")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="dependencies", to="self_study.bridgeplan")),
                ("predecessor_node", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="outgoing_dependencies", to="self_study.bridgeplannode")),
                ("successor_node", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incoming_dependencies", to="self_study.bridgeplannode")),
            ],
            options={"db_table":"self_study_bridge_plan_dependency", "constraints":[models.UniqueConstraint(fields=("plan","graph_edge"), name="ssi_bridge_dependency_edge_unique"),models.UniqueConstraint(fields=("plan","fingerprint"), name="ssi_bridge_dependency_fp_unique")]},
        ),
    ]
