import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class BlueprintStatus(models.TextChoices):
    DRAFT="DRAFT","Draft"; VALIDATING="VALIDATING","Validating"; VALID="VALID","Valid"; INVALID="INVALID","Invalid"; PUBLISHED="PUBLISHED","Published"; SUPERSEDED="SUPERSEDED","Superseded"
class DiagnosticStatus(models.TextChoices):
    DRAFT="DRAFT","Draft"; READY="READY","Ready"; IN_PROGRESS="IN_PROGRESS","In progress"; EVALUATING="EVALUATING","Evaluating"; COMPLETED="COMPLETED","Completed"; INCONCLUSIVE="INCONCLUSIVE","Inconclusive"; CHALLENGED="CHALLENGED","Challenged"; SUPERSEDED="SUPERSEDED","Superseded"; CANCELLED="CANCELLED","Cancelled"; EXPIRED="EXPIRED","Expired"
class DiagnosticItemType(models.TextChoices):
    SINGLE_CHOICE="SINGLE_CHOICE","Single choice"; MULTIPLE_CHOICE="MULTIPLE_CHOICE","Multiple choice"; NUMERIC="NUMERIC","Numeric"; SHORT_STRUCTURED="SHORT_STRUCTURED","Short structured"; ORDERING="ORDERING","Ordering"; MATCHING="MATCHING","Matching"
class DiagnosticItemStatus(models.TextChoices):
    DRAFT="DRAFT","Draft"; VALIDATING="VALIDATING","Validating"; ACTIVE="ACTIVE","Active"; SUSPENDED="SUSPENDED","Suspended"; RETIRED="RETIRED","Retired"
class PresentationStatus(models.TextChoices):
    PENDING="PENDING","Pending"; PRESENTED="PRESENTED","Presented"; ANSWERED="ANSWERED","Answered"; SKIPPED="SKIPPED","Skipped"; EXPIRED="EXPIRED","Expired"; INVALIDATED="INVALIDATED","Invalidated"
class ScoringStatus(models.TextChoices): PENDING="PENDING","Pending"; SCORED="SCORED","Scored"; INVALID="INVALID","Invalid"
class EstimateStatus(models.TextChoices):
    UNOBSERVED="UNOBSERVED","Unobserved"; TENTATIVE="TENTATIVE","Tentative"; DEMONSTRATED="DEMONSTRATED","Demonstrated"; NOT_DEMONSTRATED="NOT_DEMONSTRATED","Not demonstrated"; UNCERTAIN="UNCERTAIN","Uncertain"; NOT_DIAGNOSABLE="NOT_DIAGNOSABLE","Not diagnosable"
class ProfileStatus(models.TextChoices): FINAL="FINAL","Final"; INCONCLUSIVE="INCONCLUSIVE","Inconclusive"; SUPERSEDED="SUPERSEDED","Superseded"; INVALIDATED="INVALIDATED","Invalidated"
class ProfileNodeClassification(models.TextChoices):
    FRONTIER="FRONTIER","Starting frontier"; DEMONSTRATED="DEMONSTRATED","Demonstrated"; GAP="GAP","Gap"; UNCERTAIN="UNCERTAIN","Uncertain"; NOT_DIAGNOSABLE="NOT_DIAGNOSABLE","Not diagnosable"; EXTERNAL_PREREQUISITE="EXTERNAL_PREREQUISITE","External prerequisite"
class ChallengeStatus(models.TextChoices): OPEN="OPEN","Open"; CHECKPOINT_OFFERED="CHECKPOINT_OFFERED","Checkpoint offered"; RETAKE_OFFERED="RETAKE_OFFERED","Retake offered"; RESOLVED="RESOLVED","Resolved"; WITHDRAWN="WITHDRAWN","Withdrawn"


class DiagnosticBlueprint(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); graph_version=models.OneToOneField("self_study.CurriculumGraphVersion",on_delete=models.PROTECT,related_name="diagnostic_blueprint")
    graph_fingerprint=models.CharField(max_length=128); algorithm_version=models.CharField(max_length=40); status=models.CharField(max_length=16,choices=BlueprintStatus.choices,default=BlueprintStatus.DRAFT)
    minimum_items=models.PositiveSmallIntegerField(default=8); maximum_items=models.PositiveSmallIntegerField(default=15); target_precision=models.DecimalField(max_digits=5,decimal_places=4,default=.25)
    stopping_policy=models.JSONField(default=dict); competency_domain_count=models.PositiveIntegerField(default=0); created_at=models.DateTimeField(auto_now_add=True); created_by=models.ForeignKey("users.User",on_delete=models.PROTECT,related_name="created_diagnostic_blueprints"); published_at=models.DateTimeField(null=True,blank=True)
    class Meta: db_table="self_study_diagnostic_blueprint"
    def save(self,*a,**kw):
        if self.pk:
            old=type(self).objects.filter(pk=self.pk).first()
            if old and old.status in {BlueprintStatus.PUBLISHED,BlueprintStatus.SUPERSEDED}: raise ValidationError("Published blueprints are immutable.",code="DIAGNOSTIC_BLUEPRINT_NOT_PUBLISHED")
        super().save(*a,**kw)

class DiagnosticBlueprintNode(models.Model):
    blueprint=models.ForeignKey(DiagnosticBlueprint,on_delete=models.CASCADE,related_name="scope_nodes"); graph_node=models.ForeignKey("self_study.CurriculumNode",on_delete=models.PROTECT,related_name="diagnostic_blueprint_memberships"); domain_key=models.CharField(max_length=128); is_entry_candidate=models.BooleanField(default=False); is_target_outcome=models.BooleanField(default=False); is_diagnosticable=models.BooleanField(default=True); exclusion_reason=models.CharField(max_length=64,blank=True); importance=models.PositiveSmallIntegerField(default=1)
    class Meta: db_table="self_study_diagnostic_blueprint_node"; constraints=[models.UniqueConstraint(fields=["blueprint","graph_node"],name="ssi_diag_blueprint_node_unique")]

class DiagnosticItem(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); blueprint=models.ForeignKey(DiagnosticBlueprint,on_delete=models.PROTECT,related_name="items"); stable_key=models.CharField(max_length=128); version=models.PositiveIntegerField(default=1); item_type=models.CharField(max_length=24,choices=DiagnosticItemType.choices); prompt=models.TextField(); response_schema=models.JSONField(); scoring_specification=models.JSONField(); difficulty_band=models.PositiveSmallIntegerField(default=2); discrimination_band=models.PositiveSmallIntegerField(default=2); language=models.CharField(max_length=16); status=models.CharField(max_length=16,choices=DiagnosticItemStatus.choices,default=DiagnosticItemStatus.DRAFT); source=models.CharField(max_length=128); generation_method=models.CharField(max_length=32,default="CURATED"); review_status=models.CharField(max_length=16,default="VALIDATED"); created_at=models.DateTimeField(auto_now_add=True); created_by=models.ForeignKey("users.User",on_delete=models.PROTECT,related_name="created_diagnostic_items")
    graph_nodes=models.ManyToManyField("self_study.CurriculumNode",through="DiagnosticItemNode",related_name="diagnostic_items")
    class Meta: db_table="self_study_diagnostic_item"; constraints=[models.UniqueConstraint(fields=["blueprint","stable_key","version"],name="ssi_diag_item_version_unique")]
    def save(self,*a,**kw):
        if self.pk and type(self).objects.filter(pk=self.pk,status__in=[DiagnosticItemStatus.ACTIVE,DiagnosticItemStatus.SUSPENDED,DiagnosticItemStatus.RETIRED]).exists(): raise ValidationError("Validated item versions are immutable.",code="DIAGNOSTIC_RESPONSE_INVALID")
        super().save(*a,**kw)
class DiagnosticItemNode(models.Model):
    item=models.ForeignKey(DiagnosticItem,on_delete=models.CASCADE); graph_node=models.ForeignKey("self_study.CurriculumNode",on_delete=models.PROTECT); weight=models.DecimalField(max_digits=5,decimal_places=4,default=1)
    class Meta: db_table="self_study_diagnostic_item_node"; constraints=[models.UniqueConstraint(fields=["item","graph_node"],name="ssi_diag_item_node_unique")]

class EntryDiagnostic(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); tenant=models.ForeignKey("users.Institution",on_delete=models.PROTECT,related_name="entry_diagnostics"); intent=models.ForeignKey("self_study.SelfStudyIntent",on_delete=models.PROTECT,related_name="entry_diagnostics"); learner=models.ForeignKey("users.User",on_delete=models.PROTECT,related_name="entry_diagnostics"); graph_version=models.ForeignKey("self_study.CurriculumGraphVersion",on_delete=models.PROTECT,related_name="entry_diagnostics"); blueprint=models.ForeignKey(DiagnosticBlueprint,on_delete=models.PROTECT,related_name="diagnostics"); graph_fingerprint=models.CharField(max_length=128); policy_snapshot=models.ForeignKey("self_study.EffectiveLearningPolicySnapshot",on_delete=models.PROTECT,related_name="entry_diagnostics"); status=models.CharField(max_length=16,choices=DiagnosticStatus.choices,default=DiagnosticStatus.READY); purpose_disclosed_at=models.DateTimeField(); algorithm_version=models.CharField(max_length=40); item_bank_version=models.CharField(max_length=40); maximum_items=models.PositiveSmallIntegerField(); minimum_items=models.PositiveSmallIntegerField(); started_at=models.DateTimeField(null=True,blank=True); completed_at=models.DateTimeField(null=True,blank=True); expires_at=models.DateTimeField(); current_sequence=models.PositiveSmallIntegerField(default=0); prior_diagnostic=models.ForeignKey("self",null=True,blank=True,on_delete=models.PROTECT,related_name="retakes"); version=models.PositiveIntegerField(default=1); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        db_table="self_study_entry_diagnostic"; indexes=[models.Index(fields=["intent","status"],name="ssi_diag_intent_status_idx"),models.Index(fields=["learner","created_at"],name="ssi_diag_learner_history_idx")]; constraints=[models.UniqueConstraint(fields=["intent"],condition=Q(status__in=["READY","IN_PROGRESS","EVALUATING"]),name="ssi_diag_one_active_per_intent")]

class DiagnosticItemPresentation(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); diagnostic=models.ForeignKey(EntryDiagnostic,on_delete=models.PROTECT,related_name="presentations"); item=models.ForeignKey(DiagnosticItem,on_delete=models.PROTECT,related_name="presentations"); sequence=models.PositiveSmallIntegerField(); selection_reason_code=models.CharField(max_length=64); presented_at=models.DateTimeField(auto_now_add=True); answered_at=models.DateTimeField(null=True,blank=True); status=models.CharField(max_length=16,choices=PresentationStatus.choices,default=PresentationStatus.PRESENTED)
    class Meta: db_table="self_study_diagnostic_presentation"; constraints=[models.UniqueConstraint(fields=["diagnostic","sequence"],name="ssi_diag_sequence_unique"),models.UniqueConstraint(fields=["diagnostic"],condition=Q(status="PRESENTED"),name="ssi_diag_one_outstanding")]; indexes=[models.Index(fields=["diagnostic","status"],name="ssi_diag_present_status_idx")]
class DiagnosticResponse(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); diagnostic=models.ForeignKey(EntryDiagnostic,on_delete=models.PROTECT,related_name="responses"); presentation=models.OneToOneField(DiagnosticItemPresentation,on_delete=models.PROTECT,related_name="response"); item=models.ForeignKey(DiagnosticItem,on_delete=models.PROTECT,related_name="responses"); response_payload=models.JSONField(); response_hash=models.CharField(max_length=128); submitted_at=models.DateTimeField(auto_now_add=True); scoring_status=models.CharField(max_length=16,choices=ScoringStatus.choices,default=ScoringStatus.PENDING); score_result=models.JSONField(default=dict); scoring_algorithm_version=models.CharField(max_length=40); idempotency_key=models.CharField(max_length=128)
    class Meta: db_table="self_study_diagnostic_response"; constraints=[models.UniqueConstraint(fields=["diagnostic","idempotency_key"],name="ssi_diag_response_idem_unique")]; indexes=[models.Index(fields=["diagnostic","submitted_at"],name="ssi_diag_response_idx")]
    def save(self,*a,**kw):
        if self.pk and type(self).objects.filter(pk=self.pk,scoring_status=ScoringStatus.SCORED).exists(): raise ValidationError("Accepted responses are immutable.",code="DIAGNOSTIC_RESPONSE_CONFLICT")
        super().save(*a,**kw)
class DiagnosticCompetencyEstimate(models.Model):
    diagnostic=models.ForeignKey(EntryDiagnostic,on_delete=models.PROTECT,related_name="estimates"); graph_node=models.ForeignKey("self_study.CurriculumNode",on_delete=models.PROTECT,related_name="diagnostic_estimates"); estimate=models.DecimalField(max_digits=5,decimal_places=4,default=0); confidence=models.DecimalField(max_digits=5,decimal_places=4,default=0); uncertainty=models.DecimalField(max_digits=5,decimal_places=4,default=1); evidence_count=models.PositiveSmallIntegerField(default=0); correct_evidence_count=models.PositiveSmallIntegerField(default=0); incorrect_evidence_count=models.PositiveSmallIntegerField(default=0); status=models.CharField(max_length=24,choices=EstimateStatus.choices,default=EstimateStatus.UNOBSERVED); algorithm_version=models.CharField(max_length=40); updated_at=models.DateTimeField(auto_now=True)
    class Meta: db_table="self_study_diagnostic_estimate"; constraints=[models.UniqueConstraint(fields=["diagnostic","graph_node"],name="ssi_diag_estimate_node_unique")]; indexes=[models.Index(fields=["diagnostic","status"],name="ssi_diag_estimate_status_idx")]
class DiagnosticPlacementProfile(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); diagnostic=models.OneToOneField(EntryDiagnostic,on_delete=models.PROTECT,related_name="placement_profile"); tenant=models.ForeignKey("users.Institution",on_delete=models.PROTECT,related_name="diagnostic_profiles"); intent=models.ForeignKey("self_study.SelfStudyIntent",on_delete=models.PROTECT,related_name="diagnostic_profiles"); learner=models.ForeignKey("users.User",on_delete=models.PROTECT,related_name="diagnostic_profiles"); graph_version=models.ForeignKey("self_study.CurriculumGraphVersion",on_delete=models.PROTECT,related_name="diagnostic_profiles"); graph_fingerprint=models.CharField(max_length=128); status=models.CharField(max_length=16,choices=ProfileStatus.choices); algorithm_version=models.CharField(max_length=40); profile_fingerprint=models.CharField(max_length=128,unique=True); overall_confidence=models.DecimalField(max_digits=5,decimal_places=4); thresholds=models.JSONField(); created_at=models.DateTimeField(auto_now_add=True); supersedes=models.OneToOneField("self",null=True,blank=True,on_delete=models.PROTECT,related_name="superseded_by")
    class Meta: db_table="self_study_diagnostic_profile"; indexes=[models.Index(fields=["graph_version","status"],name="ssi_diag_profile_graph_idx")]
    def save(self,*a,**kw):
        if self.pk and type(self).objects.filter(pk=self.pk).exists(): raise ValidationError("Placement profiles are immutable.",code="DIAGNOSTIC_ALREADY_COMPLETED")
        super().save(*a,**kw)
class DiagnosticPlacementNode(models.Model):
    profile=models.ForeignKey(DiagnosticPlacementProfile,on_delete=models.PROTECT,related_name="classified_nodes"); graph_node=models.ForeignKey("self_study.CurriculumNode",on_delete=models.PROTECT,related_name="diagnostic_placements"); classification=models.CharField(max_length=32,choices=ProfileNodeClassification.choices); estimate=models.ForeignKey(DiagnosticCompetencyEstimate,null=True,blank=True,on_delete=models.PROTECT,related_name="profile_memberships")
    class Meta: db_table="self_study_diagnostic_profile_node"; constraints=[models.UniqueConstraint(fields=["profile","graph_node","classification"],name="ssi_diag_profile_node_unique")]
class DiagnosticPlacementChallenge(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); diagnostic=models.ForeignKey(EntryDiagnostic,on_delete=models.PROTECT,related_name="challenges"); profile=models.ForeignKey(DiagnosticPlacementProfile,on_delete=models.PROTECT,related_name="challenges"); reason=models.TextField(); status=models.CharField(max_length=24,choices=ChallengeStatus.choices,default=ChallengeStatus.OPEN); created_at=models.DateTimeField(auto_now_add=True); resolved_at=models.DateTimeField(null=True,blank=True)
    class Meta: db_table="self_study_diagnostic_challenge"; indexes=[models.Index(fields=["diagnostic","status"],name="ssi_diag_challenge_idx")]
