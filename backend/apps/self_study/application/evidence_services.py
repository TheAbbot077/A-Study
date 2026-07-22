from collections import Counter
from decimal import Decimal
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.utils import timezone
from apps.core.events import BusinessEvent,EventPublisher
from apps.content_processing.domain.extraction import DocumentExtraction,ExtractedBlockType,ExtractionStatus
from apps.content_processing.domain.models import JobStatus
from ..application.services import ensure_access,_has_institutional_authority
from ..domain.evidence_mapping import VERSIONS,coverage_state,fingerprint,lexical_score,mapping_decision,normalize
from ..evidence_models import *
from ..graph_models import GraphVersionStatus,NodeType
from ..models import IntentStatus,ResourceAcquisitionDecision,SelfStudyIntent

POLICY_VERSION="pi-6f.5-coverage-policy-v1";MAX_CANDIDATES=5;MAX_UNITS=5000
def publish(events,name,payload):events.publish(BusinessEvent.create(name,payload=payload))
def govern(actor,tenant):
 if not(actor.is_superuser or _has_institutional_authority(actor,tenant)):raise PermissionDenied("MAPPING_ACCESS_DENIED")
def transition(run,allowed,target):
 if run.status not in allowed:raise ValidationError("Invalid mapping lifecycle transition.",code="MAPPING_INVALID_TRANSITION")
 run.status=target;run.stage=target;run.version+=1;run.save(update_fields=["status","stage","version","updated_at"])

class CreateEvidenceMappingRunService:
 def __init__(self,events=None,enqueue=True):self.events=events or EventPublisher();self.enqueue=enqueue
 @transaction.atomic
 def execute(self,*,intent_id,resource_ids,actor):
  intent=SelfStudyIntent.objects.select_for_update().get(id=intent_id);ensure_access(actor,intent,mutate=True)
  if intent.status!=IntentStatus.ACTIVE:raise ValidationError("Active intent required.",code="MAPPING_GRAPH_NOT_AVAILABLE")
  graph=intent.curriculum_graphs.filter(current_version__status=GraphVersionStatus.PUBLISHED,status="PUBLISHED").select_related("current_version").first()
  if not graph:raise ValidationError("Published graph required.",code="MAPPING_GRAPH_NOT_PUBLISHED")
  from apps.academic.models import LearningResource
  resources=list(LearningResource.objects.filter(id__in=resource_ids,institution=intent.tenant,status="active").order_by("id"))
  if len(resources)!=len(set(resource_ids)):raise ValidationError("Eligible tenant resources required.",code="MAPPING_NO_ELIGIBLE_RESOURCES")
  inputs=[]
  for resource in resources:
   extraction=DocumentExtraction.objects.filter(resource=resource,status__in=[ExtractionStatus.COMPLETED,ExtractionStatus.COMPLETED_WITH_WARNINGS],job__status__in=[JobStatus.READY_FOR_REVIEW,JobStatus.READY_FOR_TEACHING]).select_related("job","stored_file").order_by("-completed_at").first()
   if not extraction:raise ValidationError("Extraction is not ready.",code="MAPPING_EXTRACTION_NOT_READY")
   authorization=ResourceAcquisitionDecision.objects.filter(intent=intent,content_hash=extraction.stored_file.checksum,decision__in=["AUTO_APPROVED","LINK_ONLY"]).order_by("-created_at").first()
   licence=(authorization.candidate_metadata.get("licence_category") if authorization else "UNKNOWN")
   permitted=bool(authorization and (licence in intent.effective_policy_snapshot.allowed_licence_categories or (licence=="UNKNOWN" and intent.effective_policy_snapshot.unknown_licence_allowed)))
   inputs.append({"resource":str(resource.id),"stored_file":str(extraction.stored_file_id),"job":str(extraction.job_id),"extraction":str(extraction.id),"checksum":extraction.result_checksum,"status":resource.status,"licence":"PERMITTED" if permitted else "UNKNOWN","licence_category":licence,"safety":"SAFE" if authorization else "UNVERIFIED"})
  manifest={"tenant":str(intent.tenant_id),"intent":str(intent.id),"graph_version":str(graph.current_version_id),"graph_fingerprint":graph.current_version.graph_fingerprint,"resources":inputs,"algorithms":VERSIONS,"policy":POLICY_VERSION};digest=fingerprint(manifest)
  existing=EvidenceMappingRun.objects.filter(tenant=intent.tenant,run_fingerprint=digest).exclude(status__in=[MappingRunStatus.INVALIDATED,MappingRunStatus.SUPERSEDED]).first()
  if existing:return existing,True
  run=EvidenceMappingRun.objects.create(tenant=intent.tenant,intent=intent,graph_version=graph.current_version,input_manifest=manifest,run_fingerprint=digest,algorithm_versions=VERSIONS,policy_version=POLICY_VERSION,requested_by=actor)
  for ordinal,(resource,item) in enumerate(zip(resources,inputs),1):EvidenceMappingRunResource.objects.create(run=run,resource=resource,stored_file_id=item["stored_file"],processing_job_id=item["job"],extraction_id=item["extraction"],ordinal=ordinal,source_status=item["status"],licence_disposition=item["licence"],safety_disposition=item["safety"])
  transaction.on_commit(lambda:self._after(run));return run,False
 def _after(self,run):
  publish(self.events,"self_study.evidence_mapping_run.created",{"tenant_id":str(run.tenant_id),"run_id":str(run.id),"graph_version_id":str(run.graph_version_id)})
  if self.enqueue:
   from ..infrastructure.celery.tasks import build_content_evidence_task
   build_content_evidence_task.delay(str(run.id))

class BuildContentEvidenceService:
 @transaction.atomic
 def execute(self,run_id):
  run=EvidenceMappingRun.objects.select_for_update().get(id=run_id)
  if run.status!=MappingRunStatus.PENDING:return run
  transition(run,{MappingRunStatus.PENDING},MappingRunStatus.BUILDING_EVIDENCE);ordinal=0;seen={}
  for source in run.resource_inputs.select_related("extraction").order_by("ordinal"):
   for block in source.extraction.blocks.order_by("sequence_number")[:MAX_UNITS]:
    text=block.raw_text or block.normalized_text;normalized=normalize(text)
    if not normalized:continue
    ordinal+=1;digest=fingerprint(normalized);cluster=seen.setdefault(digest,fingerprint([run.run_fingerprint,digest]));kind=block.block_type.casefold();etype="HEADING" if kind in {"title","heading_1","heading_2","heading_3"} else "TABLE" if kind in {"table","table_row","table_cell"} else "FORMULA" if kind=="equation" else "FIGURE_CAPTION" if kind=="caption" else "OTHER" if kind in {"header","footer","page_number","toc_entry"} else "PROSE";substantive=etype not in {"HEADING","OTHER"}
    ContentEvidenceUnit.objects.create(tenant=run.tenant,run=run,source_input=source,source_block=block,ordinal=ordinal,page_reference=block.page_reference,evidence_type=etype,structural_role=block.block_type,source_text=text,source_text_digest=fingerprint(text),normalized_text_digest=digest,extraction_confidence=Decimal(str(block.confidence)),citation_snapshot={"resource_id":str(source.resource_id),"stored_file_id":str(source.stored_file_id),"extraction_id":str(source.extraction_id),"block_id":str(block.id),"page":block.page_reference},licence_disposition=source.licence_disposition,safety_disposition=source.safety_disposition,duplicate_cluster=cluster,identity_fingerprint=fingerprint([run.tenant_id,source.stored_file_id,source.extraction_id,block.id,block.page_reference,digest,VERSIONS["normalization"],VERSIONS["evidence"]]),is_substantive=substantive)
  transition(run,{MappingRunStatus.BUILDING_EVIDENCE},MappingRunStatus.EVIDENCE_READY);transaction.on_commit(lambda:self._next(run));return run
 def _next(self,run):
  publish(EventPublisher(),"self_study.content_evidence.built",{"run_id":str(run.id),"unit_count":run.evidence_units.count()})
  from ..infrastructure.celery.tasks import generate_evidence_candidates_task
  generate_evidence_candidates_task.delay(str(run.id))

class GenerateEvidenceMappingCandidatesService:
 @transaction.atomic
 def execute(self,run_id):
  run=EvidenceMappingRun.objects.select_for_update().get(id=run_id)
  if run.status!=MappingRunStatus.EVIDENCE_READY:return run
  transition(run,{MappingRunStatus.EVIDENCE_READY},MappingRunStatus.MAPPING);nodes=list(run.graph_version.nodes.filter(node_type__in=[NodeType.OUTCOME,NodeType.COMPETENCY,NodeType.CONCEPT,NodeType.ASSESSMENT_OBJECTIVE,NodeType.EXTERNAL_PREREQUISITE]))
  for unit in run.evidence_units.order_by("ordinal"):
   ranked=sorted(((lexical_score(unit.source_text,n.title,n.description),n) for n in nodes),key=lambda x:(-x[0],x[1].stable_key))[:MAX_CANDIDATES]
   for rank,(score,node) in enumerate(ranked,1):
    if score<=0:continue
    EvidenceMappingCandidate.objects.create(tenant=run.tenant,run=run,evidence_unit=unit,graph_node=node,graph_node_type=node.node_type,method="LEXICAL",lexical_score=score,semantic_score=None,structural_score=0,combined_score=score,rank=rank,rationale_codes=["LEXICAL_OVERLAP","SEMANTIC_UNAVAILABLE"],algorithm_version=VERSIONS["candidates"],candidate_fingerprint=fingerprint([unit.identity_fingerprint,node.stable_key,score,VERSIONS["candidates"]]))
  DecideCurriculumEvidenceMappingsService().execute_locked(run);return run

class DecideCurriculumEvidenceMappingsService:
 def execute_locked(self,run):
  for candidate in run.candidates.select_related("evidence_unit","graph_node").order_by("evidence_unit__ordinal","rank"):
   unit=candidate.evidence_unit;status,classification,codes=mapping_decision(unit.evidence_type,candidate.graph_node_type,candidate.combined_score,unit.is_substantive,unit.safety_disposition=="SAFE",unit.licence_disposition=="PERMITTED")
   CurriculumEvidenceMapping.objects.create(tenant=run.tenant,run=run,candidate=candidate,evidence_unit=unit,graph_node=candidate.graph_node,graph_node_type=candidate.graph_node_type,classification=classification,status=status,confidence_band="HIGH" if candidate.combined_score>=Decimal(".8") else "MEDIUM",scores={"lexical":str(candidate.lexical_score)},rule_codes=codes,rationale_codes=candidate.rationale_codes,citation_snapshot=unit.citation_snapshot,algorithm_version=VERSIONS["acceptance"],policy_version=run.policy_version,mapping_fingerprint=fingerprint([candidate.candidate_fingerprint,status,classification,VERSIONS["acceptance"]]))
  transition(run,{MappingRunStatus.MAPPING},MappingRunStatus.MAPPINGS_READY);transaction.on_commit(lambda:self._next(run))
 def _next(self,run):
  publish(EventPublisher(),"self_study.evidence_mapping.completed",{"run_id":str(run.id),"mapping_count":run.mappings.count()})
  from ..infrastructure.celery.tasks import evaluate_curriculum_coverage_task
  evaluate_curriculum_coverage_task.delay(str(run.id))

class EvaluateCurriculumCoverageService:
 @transaction.atomic
 def execute(self,run_id):
  run=EvidenceMappingRun.objects.select_for_update().get(id=run_id)
  if run.status==MappingRunStatus.COMPLETED:return run.coverage_evaluations.get(status=CoverageStatus.COMPLETED)
  if run.status!=MappingRunStatus.MAPPINGS_READY:raise ValidationError("Mappings are incomplete.",code="COVERAGE_UNEVALUATED")
  transition(run,{MappingRunStatus.MAPPINGS_READY},MappingRunStatus.EVALUATING_COVERAGE);mappings=list(run.mappings.select_related("evidence_unit__source_input","graph_node").order_by("mapping_fingerprint"));mapping_fp=fingerprint([x.mapping_fingerprint for x in mappings]);evaluation=CurriculumCoverageEvaluation.objects.create(tenant=run.tenant,run=run,graph_version=run.graph_version,mapping_set_fingerprint=mapping_fp,algorithm_version=VERSIONS["coverage"],policy_version=run.policy_version,status=CoverageStatus.RUNNING,evaluation_fingerprint=fingerprint([run.run_fingerprint,mapping_fp,VERSIONS["coverage"],run.policy_version]),input_summary={"mappings":len(mappings)})
  gaps=[];counts=Counter()
  for node in run.graph_version.nodes.order_by("stable_key"):
   rows=[{"status":x.status,"classification":x.classification,"source":str(x.evidence_unit.source_input.resource_id)} for x in mappings if x.graph_node_id==node.id];state,codes=coverage_state(rows,applicable=node.node_type not in {NodeType.CURRICULUM_ROOT,NodeType.STAGE,NodeType.MODULE,NodeType.TOPIC});counts[state]+=1
   accepted=[x for x in rows if x["status"]==MappingStatus.ACCEPTED];direct=sum(x["classification"]==MappingClass.DIRECT for x in accepted);conflicts=sum(x["classification"]==MappingClass.CONFLICTING for x in accepted)
   CurriculumNodeCoverage.objects.create(evaluation=evaluation,graph_node=node,node_type=node.node_type,state=state,sufficiency_score=Decimal("1") if state==CoverageState.COVERED else Decimal(".5") if state==CoverageState.PARTIAL else 0,direct_count=direct,supporting_count=sum(x["classification"]==MappingClass.SUPPORTING for x in accepted),prerequisite_count=sum(x["classification"]==MappingClass.PREREQUISITE_SUPPORT for x in accepted),assessment_count=sum(x["classification"]==MappingClass.ASSESSMENT_SUPPORT for x in accepted),conflicting_count=conflicts,distinct_source_count=len({x["source"] for x in accepted}),accepted_mapping_count=len(accepted),excluded_count=len(rows)-len(accepted),rationale_codes=codes,blocker_count=int(state in {CoverageState.MISSING,CoverageState.CONFLICTING}),citation_set_fingerprint=fingerprint(sorted(x["source"] for x in accepted)))
   if state in {CoverageState.MISSING,CoverageState.PARTIAL,CoverageState.CONFLICTING}:gaps.append(str(node.id))
   for code in codes:CoverageFinding.objects.create(evaluation=evaluation,code=code,severity="BLOCKER" if state in {CoverageState.MISSING,CoverageState.CONFLICTING} else "WARNING",blocking=state in {CoverageState.MISSING,CoverageState.CONFLICTING},scope_type="GRAPH_NODE",scope_identifier=str(node.id),graph_node=node,details={"state":state},algorithm_version=VERSIONS["coverage"],policy_version=run.policy_version)
  evaluation.status=CoverageStatus.COMPLETED;evaluation.gap_set_fingerprint=fingerprint(sorted(gaps));evaluation.input_summary={**evaluation.input_summary,"states":dict(counts),"gap_node_ids":sorted(gaps)};evaluation.completed_at=timezone.now();evaluation.save(update_fields=["status","gap_set_fingerprint","input_summary","completed_at"]);run.status=MappingRunStatus.COMPLETED;run.stage="COMPLETED";run.completed_at=timezone.now();run.save(update_fields=["status","stage","completed_at","updated_at"]);transaction.on_commit(lambda:publish(EventPublisher(),"self_study.curriculum_coverage.completed",{"run_id":str(run.id),"evaluation_id":str(evaluation.id),"gap_set_fingerprint":evaluation.gap_set_fingerprint,"node_states":dict(counts)}));return evaluation

class InvalidateEvidenceMappingRunService:
 @transaction.atomic
 def execute(self,run_id,actor,reason="MAPPING_INVALIDATED"):
  run=EvidenceMappingRun.objects.select_for_update().get(id=run_id);govern(actor,run.tenant_id);run.status=MappingRunStatus.INVALIDATED;run.failure_code=reason;run.version+=1;run.save(update_fields=["status","failure_code","version","updated_at"]);run.mappings.filter(status__in=[MappingStatus.ACCEPTED,MappingStatus.PROPOSED]).update(status=MappingStatus.INVALIDATED);run.coverage_evaluations.filter(status=CoverageStatus.COMPLETED).update(status=CoverageStatus.INVALIDATED);transaction.on_commit(lambda:publish(EventPublisher(),"self_study.evidence_mapping.invalidated",{"run_id":str(run.id),"reason":reason}));return run

class RecalculateCurriculumCoverageService:
 @transaction.atomic
 def execute(self,run_id,actor):
  prior=EvidenceMappingRun.objects.select_for_update().get(id=run_id);govern(actor,prior.tenant_id)
  if prior.status!=MappingRunStatus.COMPLETED:raise ValidationError("Completed run required.",code="COVERAGE_NO_CURRENT_EVALUATION")
  prior.status=MappingRunStatus.SUPERSEDED;prior.save(update_fields=["status","updated_at"])
  successor=EvidenceMappingRun.objects.create(tenant=prior.tenant,intent=prior.intent,graph_version=prior.graph_version,status=MappingRunStatus.PENDING,stage="CREATED",input_manifest=prior.input_manifest,run_fingerprint=fingerprint([prior.run_fingerprint,VERSIONS, POLICY_VERSION,str(prior.id)]),algorithm_versions=VERSIONS,policy_version=POLICY_VERSION,requested_by=actor,predecessor=prior)
  for source in prior.resource_inputs.all():EvidenceMappingRunResource.objects.create(run=successor,resource=source.resource,stored_file=source.stored_file,processing_job=source.processing_job,extraction=source.extraction,ordinal=source.ordinal,source_status=source.source_status,licence_disposition=source.licence_disposition,safety_disposition=source.safety_disposition)
  transaction.on_commit(lambda:self._enqueue(successor.id))
  return successor
 def _enqueue(self,run_id):
  from ..infrastructure.celery.tasks import build_content_evidence_task
  build_content_evidence_task.delay(str(run_id))

class RetireEvidenceSourceService:
 @transaction.atomic
 def execute(self,resource_id):
  runs=EvidenceMappingRun.objects.select_for_update().filter(resource_inputs__resource_id=resource_id,status=MappingRunStatus.COMPLETED).distinct()
  ids=[]
  for run in runs:
   run.status=MappingRunStatus.STALE;run.failure_code="SOURCE_RETIRED";run.save(update_fields=["status","failure_code","updated_at"]);run.mappings.filter(evidence_unit__source_input__resource_id=resource_id,status=MappingStatus.ACCEPTED).update(status=MappingStatus.STALE);run.coverage_evaluations.filter(status=CoverageStatus.COMPLETED).update(status=CoverageStatus.STALE);ids.append(str(run.id))
  transaction.on_commit(lambda:publish(EventPublisher(),"self_study.evidence_source.retired",{"resource_id":str(resource_id),"run_ids":ids}));return ids

class InvalidateMappingsForGraphService:
 @transaction.atomic
 def execute(self,graph_version_id,reason="COVERAGE_GRAPH_SUPERSEDED"):
  runs=EvidenceMappingRun.objects.select_for_update().filter(graph_version_id=graph_version_id,status__in=[MappingRunStatus.PENDING,MappingRunStatus.EVIDENCE_READY,MappingRunStatus.MAPPINGS_READY,MappingRunStatus.COMPLETED]);ids=[]
  for run in runs:
   run.status=MappingRunStatus.STALE if reason=="COVERAGE_GRAPH_SUPERSEDED" else MappingRunStatus.INVALIDATED;run.failure_code=reason;run.save(update_fields=["status","failure_code","updated_at"]);run.mappings.filter(status=MappingStatus.ACCEPTED).update(status=MappingStatus.STALE if run.status==MappingRunStatus.STALE else MappingStatus.INVALIDATED);run.coverage_evaluations.filter(status=CoverageStatus.COMPLETED).update(status=CoverageStatus.STALE if run.status==MappingRunStatus.STALE else CoverageStatus.INVALIDATED);ids.append(str(run.id))
  event="self_study.curriculum_coverage.stale" if reason=="COVERAGE_GRAPH_SUPERSEDED" else "self_study.curriculum_coverage.invalidated";transaction.on_commit(lambda:publish(EventPublisher(),event,{"graph_version_id":str(graph_version_id),"run_ids":ids,"reason":reason}));return ids

class FailEvidenceMappingRunService:
 @transaction.atomic
 def execute(self,run_id,code="MAPPING_STAGE_FAILED"):
  run=EvidenceMappingRun.objects.select_for_update().get(id=run_id)
  if run.status in {MappingRunStatus.COMPLETED,MappingRunStatus.INVALIDATED,MappingRunStatus.SUPERSEDED}:return run
  run.status=MappingRunStatus.FAILED;run.failure_code=code;run.failure_detail="Evidence mapping could not complete.";run.save(update_fields=["status","failure_code","failure_detail","updated_at"]);event="self_study.curriculum_coverage.failed" if code.startswith("COVERAGE_") else "self_study.evidence_mapping.failed";transaction.on_commit(lambda:publish(EventPublisher(),event,{"run_id":str(run.id),"failure_code":code}));return run
