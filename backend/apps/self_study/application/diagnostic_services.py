from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.utils import timezone
from apps.core.events import BusinessEvent,EventPublisher
from ..application.services import ensure_access,_has_institutional_authority
from ..diagnostic_models import *
from ..domain.entry_diagnostic import *
from ..graph_models import CurriculumGraphVersion,EdgeType,GraphVersionStatus,NodeType
from ..models import IntentStatus,SelfStudyIntent

def _event(events,name,payload): events.publish(BusinessEvent.create(name,payload=payload))
def _governor(actor,tenant):
    if not (actor.is_superuser or _has_institutional_authority(actor,tenant)): raise PermissionDenied("DIAGNOSTIC_ACCESS_DENIED")
def _assert_graph(version):
    if version.status!=GraphVersionStatus.PUBLISHED: raise ValidationError("A published curriculum graph is required.",code="PUBLISHED_CURRICULUM_GRAPH_REQUIRED")
    if not version.graph_fingerprint: raise ValidationError("The graph fingerprint is invalid.",code="CURRICULUM_GRAPH_INVALIDATED")

class BuildDiagnosticBlueprintService:
    def __init__(self,events=None):self.events=events or EventPublisher()
    @transaction.atomic
    def execute(self,graph_version_id,actor,minimum_items=8,maximum_items=15):
        version=CurriculumGraphVersion.objects.select_for_update().get(id=graph_version_id); _assert_graph(version); _governor(actor,version.graph.tenant_id)
        existing=DiagnosticBlueprint.objects.filter(graph_version=version).first()
        if existing:return existing,True
        if minimum_items<2 or maximum_items<minimum_items or maximum_items>50: raise ValidationError("Item bounds are invalid.",code="DIAGNOSTIC_ITEM_BANK_INSUFFICIENT")
        blueprint=DiagnosticBlueprint.objects.create(graph_version=version,graph_fingerprint=version.graph_fingerprint,algorithm_version=ALGORITHM_VERSION,minimum_items=minimum_items,maximum_items=maximum_items,created_by=actor,stopping_policy={"precision":"0.25","frontier_confirmation_items":2})
        nodes=version.nodes.filter(node_type__in=[NodeType.COMPETENCY,NodeType.CONCEPT,NodeType.EXTERNAL_PREREQUISITE,NodeType.OUTCOME]).order_by("ordinal","stable_key")
        memberships=[]; domains=set()
        for node in nodes:
            diagnosticable=node.node_type!=NodeType.OUTCOME and node.metadata.get("diagnostic_channel","AUTOMATED") not in {"PHYSICAL","LABORATORY","ORAL","SUPERVISED","NONE"}
            domain=str(node.metadata.get("domain_key") or node.metadata.get("strand") or "default");domains.add(domain)
            memberships.append(DiagnosticBlueprintNode(blueprint=blueprint,graph_node=node,domain_key=domain,is_entry_candidate=node.node_type in {NodeType.CONCEPT,NodeType.COMPETENCY},is_target_outcome=node.node_type==NodeType.OUTCOME,is_diagnosticable=diagnosticable,exclusion_reason="" if diagnosticable else "CHANNEL_UNSUPPORTED",importance=int(node.metadata.get("diagnostic_importance",1))))
        DiagnosticBlueprintNode.objects.bulk_create(memberships);blueprint.competency_domain_count=len(domains);blueprint.save(update_fields=["competency_domain_count"])
        transaction.on_commit(lambda:_event(self.events,"self_study.diagnostic_blueprint_created",{"blueprint_id":str(blueprint.id),"graph_version_id":str(version.id)}));return blueprint,False

class RegisterDiagnosticItemService:
    @transaction.atomic
    def execute(self,*,blueprint_id,actor,graph_node_ids,**fields):
        blueprint=DiagnosticBlueprint.objects.select_for_update().get(id=blueprint_id);_governor(actor,blueprint.graph_version.graph.tenant_id)
        if blueprint.status!=BlueprintStatus.DRAFT:raise ValidationError("Blueprint is immutable.",code="DIAGNOSTIC_BLUEPRINT_NOT_PUBLISHED")
        allowed=set(blueprint.scope_nodes.filter(is_diagnosticable=True).values_list("graph_node_id",flat=True))
        if not graph_node_ids or not set(graph_node_ids)<=allowed:raise ValidationError("Every item needs diagnosticable graph nodes.",code="DIAGNOSTIC_RESPONSE_INVALID")
        scoring=fields.get("scoring_specification")
        if not isinstance(scoring,dict) or "answer" not in scoring:
            raise ValidationError("A deterministic server-side scoring key is required.",code="DIAGNOSTIC_RESPONSE_INVALID")
        schema=fields.get("response_schema")
        if not isinstance(schema,dict):raise ValidationError("A response schema is required.",code="DIAGNOSTIC_RESPONSE_INVALID")
        try:validate_response(fields["item_type"],schema,{"answer":scoring["answer"]})
        except ValueError as exc:raise ValidationError("The scoring key does not satisfy the response schema.",code="DIAGNOSTIC_RESPONSE_INVALID") from exc
        item=DiagnosticItem.objects.create(blueprint=blueprint,created_by=actor,**fields)
        DiagnosticItemNode.objects.bulk_create([DiagnosticItemNode(item=item,graph_node_id=x) for x in graph_node_ids]);return item
class PublishDiagnosticBlueprintService:
    @transaction.atomic
    def execute(self,blueprint_id,actor):
        bp=DiagnosticBlueprint.objects.select_for_update().get(id=blueprint_id);_governor(actor,bp.graph_version.graph.tenant_id);_assert_graph(bp.graph_version)
        active=bp.items.filter(status=DiagnosticItemStatus.ACTIVE,review_status="VALIDATED")
        covered=set(DiagnosticItemNode.objects.filter(item__in=active).values_list("graph_node_id",flat=True));required=set(bp.scope_nodes.filter(is_diagnosticable=True).values_list("graph_node_id",flat=True))
        if active.count()<bp.minimum_items or not required<=covered:bp.status=BlueprintStatus.INVALID;bp.save(update_fields=["status"]);raise ValidationError("Published item coverage is insufficient.",code="DIAGNOSTIC_ITEM_BANK_INSUFFICIENT")
        bp.status=BlueprintStatus.PUBLISHED;bp.published_at=timezone.now();bp.save(update_fields=["status","published_at"]);return bp

class CreateEntryDiagnosticService:
    def __init__(self,events=None):self.events=events or EventPublisher()
    @transaction.atomic
    def execute(self,*,intent_id,actor,purpose_acknowledged,prior_diagnostic=None):
        intent=SelfStudyIntent.objects.select_for_update().get(id=intent_id);ensure_access(actor,intent,mutate=True)
        if intent.status!=IntentStatus.ACTIVE or not intent.effective_policy_snapshot_id:raise ValidationError("An active intent policy is required.",code="POLICY_SNAPSHOT_REQUIRED")
        if not purpose_acknowledged:raise ValidationError("Diagnostic purpose disclosure must be acknowledged.",code="DIAGNOSTIC_DISCLOSURE_REQUIRED")
        graph=intent.curriculum_graphs.filter(status="PUBLISHED",current_version__status=GraphVersionStatus.PUBLISHED).select_related("current_version__diagnostic_blueprint").order_by("-updated_at").first()
        if not graph:raise ValidationError("A published curriculum graph is required.",code="PUBLISHED_CURRICULUM_GRAPH_REQUIRED")
        version=graph.current_version;_assert_graph(version)
        try:bp=version.diagnostic_blueprint
        except DiagnosticBlueprint.DoesNotExist as exc:raise ValidationError("A diagnostic blueprint is required.",code="DIAGNOSTIC_BLUEPRINT_REQUIRED") from exc
        if bp.status!=BlueprintStatus.PUBLISHED:raise ValidationError("The diagnostic blueprint is not published.",code="DIAGNOSTIC_BLUEPRINT_NOT_PUBLISHED")
        existing=intent.entry_diagnostics.filter(status__in=[DiagnosticStatus.READY,DiagnosticStatus.IN_PROGRESS,DiagnosticStatus.EVALUATING]).first()
        if existing:return existing,True
        diagnostic=EntryDiagnostic.objects.create(tenant=intent.tenant,intent=intent,learner=intent.learner,graph_version=version,blueprint=bp,graph_fingerprint=version.graph_fingerprint,policy_snapshot=intent.effective_policy_snapshot,status=DiagnosticStatus.READY,purpose_disclosed_at=timezone.now(),algorithm_version=ALGORITHM_VERSION,item_bank_version=str(bp.id),minimum_items=bp.minimum_items,maximum_items=bp.maximum_items,expires_at=timezone.now()+timedelta(days=7),prior_diagnostic=prior_diagnostic)
        transaction.on_commit(lambda:_event(self.events,"self_study.entry_diagnostic_created",{"diagnostic_id":str(diagnostic.id),"intent_id":str(intent.id),"graph_version_id":str(version.id)}));return diagnostic,False

class DiagnosticDeliveryService:
    def __init__(self,events=None):self.events=events or EventPublisher()
    @transaction.atomic
    def start(self,diagnostic_id,actor):
        d=EntryDiagnostic.objects.select_for_update().get(id=diagnostic_id);ensure_access(actor,d.intent,mutate=True)
        if d.status==DiagnosticStatus.IN_PROGRESS:return d
        if d.status!=DiagnosticStatus.READY:raise ValidationError("Diagnostic is not ready.",code="DIAGNOSTIC_NOT_READY")
        if d.expires_at<=timezone.now():d.status=DiagnosticStatus.EXPIRED;d.save(update_fields=["status"]);raise ValidationError("Diagnostic expired.",code="DIAGNOSTIC_EXPIRED")
        d.status=DiagnosticStatus.IN_PROGRESS;d.started_at=timezone.now();d.save(update_fields=["status","started_at"]);transaction.on_commit(lambda:_event(self.events,"self_study.entry_diagnostic_started",{"diagnostic_id":str(d.id)}));return d
    @transaction.atomic
    def current_item(self,diagnostic_id,actor):
        d=EntryDiagnostic.objects.select_for_update().get(id=diagnostic_id);ensure_access(actor,d.intent)
        existing=d.presentations.filter(status=PresentationStatus.PRESENTED).select_related("item").first()
        if existing:return existing
        if d.status!=DiagnosticStatus.IN_PROGRESS:raise ValidationError("Diagnostic is not in progress.",code="DIAGNOSTIC_NOT_IN_PROGRESS")
        presented=set(d.presentations.values_list("item_id",flat=True)); estimates={x.graph_node_id:x for x in d.estimates.all()}
        candidates=[]
        for item in d.blueprint.items.filter(status=DiagnosticItemStatus.ACTIVE,review_status="VALIDATED").prefetch_related("diagnosticitemnode_set__graph_node"):
            links=list(item.diagnosticitemnode_set.all()); membership=d.blueprint.scope_nodes.filter(graph_node_id=links[0].graph_node_id).first(); uncertainty=max((estimates.get(x.graph_node_id).uncertainty if estimates.get(x.graph_node_id) else Decimal(1) for x in links),default=Decimal(1))
            candidates.append(ItemCandidate(str(item.id),membership.domain_key,item.difficulty_band,membership.importance,uncertainty,item.id in presented))
        choice=select_candidate(candidates,d.responses.count())
        if not choice:return None
        item=d.blueprint.items.get(id=choice.id);d.current_sequence+=1;d.save(update_fields=["current_sequence"])
        presentation=DiagnosticItemPresentation.objects.create(diagnostic=d,item=item,sequence=d.current_sequence,selection_reason_code="UNCERTAINTY_AND_COVERAGE")
        transaction.on_commit(lambda:_event(self.events,"self_study.diagnostic_item_presented",{"diagnostic_id":str(d.id),"presentation_id":str(presentation.id),"sequence":presentation.sequence}));return presentation

class SubmitDiagnosticResponseService:
    def __init__(self,events=None):self.events=events or EventPublisher()
    @transaction.atomic
    def execute(self,*,diagnostic_id,actor,presentation_id,response_payload,idempotency_key):
        d=EntryDiagnostic.objects.select_for_update().get(id=diagnostic_id);ensure_access(actor,d.intent,mutate=True)
        if d.status!=DiagnosticStatus.IN_PROGRESS:raise ValidationError("Diagnostic is not in progress.",code="DIAGNOSTIC_NOT_IN_PROGRESS")
        digest=canonical_hash(response_payload);replay=d.responses.filter(idempotency_key=idempotency_key).first()
        if replay:
            if replay.response_hash!=digest:raise ValidationError("Idempotency payload conflicts.",code="DIAGNOSTIC_RESPONSE_CONFLICT")
            return replay,True
        try:p=d.presentations.select_for_update().select_related("item").get(id=presentation_id,status=PresentationStatus.PRESENTED)
        except DiagnosticItemPresentation.DoesNotExist as exc:raise ValidationError("Item was not presented.",code="DIAGNOSTIC_ITEM_NOT_PRESENTED") from exc
        try:validate_response(p.item.item_type,p.item.response_schema,response_payload)
        except ValueError as exc:raise ValidationError(str(exc),code="DIAGNOSTIC_RESPONSE_INVALID") from exc
        result=score_response(p.item.item_type,p.item.scoring_specification,response_payload)
        response=DiagnosticResponse.objects.create(diagnostic=d,presentation=p,item=p.item,response_payload=response_payload,response_hash=digest,scoring_status=ScoringStatus.SCORED,score_result=result,scoring_algorithm_version=SCORING_VERSION,idempotency_key=idempotency_key)
        p.status=PresentationStatus.ANSWERED;p.answered_at=timezone.now();p.save(update_fields=["status","answered_at"]);self._estimates(d,p.item,result["correctness"])
        transaction.on_commit(lambda:_event(self.events,"self_study.diagnostic_response_accepted",{"diagnostic_id":str(d.id),"response_id":str(response.id),"presentation_id":str(p.id)}));return response,False
    def _estimates(self,d,item,correct):
        for link in item.diagnosticitemnode_set.all():
            est,_=DiagnosticCompetencyEstimate.objects.get_or_create(diagnostic=d,graph_node=link.graph_node,defaults={"algorithm_version":ALGORITHM_VERSION})
            est.evidence_count+=1;est.correct_evidence_count+=int(correct);est.incorrect_evidence_count+=int(not correct);est.estimate,est.confidence,est.uncertainty,est.status=estimate_classification(est.correct_evidence_count,est.evidence_count);est.save()

class FinalizeDiagnosticPlacementService:
    def __init__(self,events=None):self.events=events or EventPublisher()
    @transaction.atomic
    def execute(self,diagnostic_id):
        d=EntryDiagnostic.objects.select_for_update().get(id=diagnostic_id)
        if hasattr(d,"placement_profile"):return d.placement_profile
        if d.status not in {DiagnosticStatus.IN_PROGRESS,DiagnosticStatus.EVALUATING}:raise ValidationError("Diagnostic cannot complete.",code="DIAGNOSTIC_NOT_IN_PROGRESS")
        estimates=list(d.estimates.select_related("graph_node"));answered=d.responses.count();demonstrated={x.graph_node_id for x in estimates if x.status==EstimateStatus.DEMONSTRATED};gaps={x.graph_node_id for x in estimates if x.status==EstimateStatus.NOT_DEMONSTRATED};uncertain={x.graph_node_id for x in estimates if x.status in {EstimateStatus.UNOBSERVED,EstimateStatus.TENTATIVE,EstimateStatus.UNCERTAIN}}
        # A frontier node must be demonstrated and may not have a required prerequisite classified as a gap.
        blocked=set(d.graph_version.edges.filter(edge_type=EdgeType.REQUIRES,requirement="REQUIRED",target_node_id__in=gaps).values_list("source_node_id",flat=True));frontier=demonstrated-blocked
        sufficient=answered>=d.minimum_items and bool(frontier) and len(uncertain)<=max(1,len(estimates)//3);status=ProfileStatus.FINAL if sufficient else ProfileStatus.INCONCLUSIVE
        pieces={"diagnostic":str(d.id),"graph":d.graph_fingerprint,"blueprint":str(d.blueprint_id),"items":sorted(str(x.item_id) for x in d.responses.all()),"responses":sorted((str(x.id),x.response_hash) for x in d.responses.all()),"estimates":sorted((str(x.graph_node_id),str(x.estimate),str(x.confidence),x.status) for x in estimates),"thresholds":[str(DEMONSTRATED_THRESHOLD),str(CONFIDENCE_THRESHOLD)],"frontier":sorted(str(x) for x in frontier),"gaps":sorted(str(x) for x in gaps),"uncertain":sorted(str(x) for x in uncertain)}
        prior_profile=getattr(d.prior_diagnostic,"placement_profile",None) if d.prior_diagnostic_id else None
        profile=DiagnosticPlacementProfile.objects.create(diagnostic=d,tenant=d.tenant,intent=d.intent,learner=d.learner,graph_version=d.graph_version,graph_fingerprint=d.graph_fingerprint,status=status,algorithm_version=PROFILE_VERSION,profile_fingerprint=profile_fingerprint(**pieces),overall_confidence=min((x.confidence for x in estimates),default=Decimal(0)),thresholds={"demonstrated":str(DEMONSTRATED_THRESHOLD),"confidence":str(CONFIDENCE_THRESHOLD)},supersedes=prior_profile if sufficient else None)
        rows=[]
        for est in estimates:
            classification=ProfileNodeClassification.FRONTIER if est.graph_node_id in frontier else ProfileNodeClassification.DEMONSTRATED if est.graph_node_id in demonstrated else ProfileNodeClassification.GAP if est.graph_node_id in gaps else ProfileNodeClassification.UNCERTAIN
            rows.append(DiagnosticPlacementNode(profile=profile,graph_node=est.graph_node,classification=classification,estimate=est))
        DiagnosticPlacementNode.objects.bulk_create(rows);d.status=DiagnosticStatus.COMPLETED if sufficient else DiagnosticStatus.INCONCLUSIVE;d.completed_at=timezone.now();d.save(update_fields=["status","completed_at"])
        if sufficient and prior_profile:
            DiagnosticPlacementProfile.objects.filter(pk=prior_profile.pk).update(status=ProfileStatus.SUPERSEDED)
            EntryDiagnostic.objects.filter(pk=d.prior_diagnostic_id).update(status=DiagnosticStatus.SUPERSEDED)
            transaction.on_commit(lambda:_event(self.events,"self_study.diagnostic_placement_superseded",{"diagnostic_id":str(d.id),"profile_id":str(prior_profile.id),"successor_profile_id":str(profile.id),"graph_version_id":str(d.graph_version_id)}))
        name="self_study.diagnostic_placement_finalized" if sufficient else "self_study.entry_diagnostic_inconclusive";transaction.on_commit(lambda:_event(self.events,name,{"diagnostic_id":str(d.id),"profile_id":str(profile.id),"graph_version_id":str(d.graph_version_id),"profile_status":profile.status}));return profile

class DiagnosticControlService:
    @transaction.atomic
    def cancel(self,d,actor):
        ensure_access(actor,d.intent,mutate=True)
        if d.status not in {DiagnosticStatus.READY,DiagnosticStatus.IN_PROGRESS}:raise ValidationError("Diagnostic cannot be cancelled.",code="DIAGNOSTIC_ALREADY_COMPLETED")
        d.status=DiagnosticStatus.CANCELLED;d.save(update_fields=["status"]);return d
    @transaction.atomic
    def challenge(self,d,actor,reason):
        ensure_access(actor,d.intent,mutate=True)
        if d.status!=DiagnosticStatus.COMPLETED or not d.policy_snapshot.learner_can_challenge:raise ValidationError("Challenge is unavailable.",code="DIAGNOSTIC_CHALLENGE_NOT_ALLOWED")
        challenge=DiagnosticPlacementChallenge.objects.create(diagnostic=d,profile=d.placement_profile,reason=reason);d.status=DiagnosticStatus.CHALLENGED;d.save(update_fields=["status"]);return challenge
    def retake(self,d,actor,purpose_acknowledged):
        ensure_access(actor,d.intent,mutate=True)
        if not d.policy_snapshot.learner_can_retake or d.status not in {DiagnosticStatus.COMPLETED,DiagnosticStatus.INCONCLUSIVE,DiagnosticStatus.CHALLENGED}:raise ValidationError("Retake is unavailable.",code="DIAGNOSTIC_RETAKE_NOT_ALLOWED")
        return CreateEntryDiagnosticService().execute(intent_id=d.intent_id,actor=actor,purpose_acknowledged=purpose_acknowledged,prior_diagnostic=d)
    @transaction.atomic
    def checkpoint(self,d,actor):
        ensure_access(actor,d.intent,mutate=True)
        if not d.policy_snapshot.learner_can_attempt_checkpoint or d.status not in {DiagnosticStatus.COMPLETED,DiagnosticStatus.INCONCLUSIVE}:
            raise ValidationError("Checkpoint is unavailable.",code="DIAGNOSTIC_CHALLENGE_NOT_ALLOWED")
        return DiagnosticPlacementChallenge.objects.create(diagnostic=d,profile=d.placement_profile,reason="Learner requested a governed checkpoint.",status=ChallengeStatus.CHECKPOINT_OFFERED)
