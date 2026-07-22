from __future__ import annotations

import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.core.events import BusinessEvent, EventPublisher

from ..application.services import _has_institutional_authority
from ..application.teaching_services import GetTeachingOrchestrationHandoffService
from ..bridge_models import BridgePlanStatus
from ..domain.bridge_planning import fingerprint
from ..domain.teaching_orchestration import (
    DISCLOSURE_POLICY_VERSION, MODEL_VERSION, ORCHESTRATION_VERSION, PRIVACY_POLICY_VERSION,
    PROMPT_POLICY_VERSION, SAFETY_POLICY_VERSION, build_context_payload, detect_prompt_injection,
    ensure_transition, finding, generation_fingerprint, safe_teaching_text, select_action,
)
from ..models import IntentStatus, SelfStudyIntent
from ..orchestration_models import (
    SelfStudyTeachingSession, SelfStudyTeachingSessionState, TeachingContextSnapshot,
    TeachingFindingSeverity, TeachingOrchestrationRun, TeachingOrchestrationRunStatus,
    TeachingSafetyStatus, TeachingSessionFinding, TeachingSessionNode,
    TeachingSessionNodeState, TeachingTransition, TeachingTransitionType, TeachingTurn,
    TeachingTurnActor, TeachingTurnCitation,
)
from ..teaching_models import (
    NodeTeachingPackStatus, TeachingPackResource, TeachingPreparationManifest,
    TeachingPreparationManifestStatus, TeachingReadinessState,
)


def _publish(name, payload):
    EventPublisher().publish(BusinessEvent.create(name, payload=payload))


def _after_commit(name, **payload):
    transaction.on_commit(lambda: _publish(name, {key: str(value) for key, value in payload.items()}))


def _govern(actor, tenant_id):
    if not (actor.is_superuser or _has_institutional_authority(actor, tenant_id)):
        raise PermissionDenied("TEACHING_SESSION_GOVERNANCE_REQUIRED")


def _audit_after_commit(*, actor, institution, action, session, metadata):
    transaction.on_commit(lambda: AuditService().record_action(actor=actor, institution=institution, action=action, target_type="SelfStudyTeachingSession", target_id=str(session.id), target_display=session.session_fingerprint, metadata=metadata))


class ValidateTeachingAuthorityService:
    def execute(self, *, intent, manifest):
        findings = []
        if intent.status != IntentStatus.ACTIVE:
            findings.append(finding("TEACHING_SESSION_INTENT_NOT_ACTIVE", [intent.id]))
        if manifest.intent_id != intent.id or manifest.tenant_id != intent.tenant_id:
            findings.append(finding("TEACHING_SESSION_TENANT_MISMATCH", [manifest.id]))
        if manifest.bridge_plan.status != BridgePlanStatus.ACTIVE:
            findings.append(finding("TEACHING_SESSION_PLAN_NOT_ACTIVE", [manifest.bridge_plan_id]))
        if manifest.status != TeachingPreparationManifestStatus.READY:
            findings.append(finding("TEACHING_SESSION_PREPARATION_NOT_READY", [manifest.id]))
        if not hasattr(manifest, "retrieval_manifest") or manifest.retrieval_manifest.status != "VERIFIED":
            findings.append(finding("TEACHING_SESSION_RETRIEVAL_NOT_VERIFIED", [manifest.id]))
        evaluation = manifest.readiness_evaluations.order_by("-created_at").first()
        if not evaluation or evaluation.state != TeachingReadinessState.READY:
            findings.append(finding("TEACHING_SESSION_PREPARATION_NOT_READY", [manifest.id], {"readiness": getattr(evaluation, "state", None)}))
        if manifest.bridge_plan.graph_version_id != manifest.graph_version_id:
            findings.append(finding("TEACHING_SESSION_GRAPH_MISMATCH", [manifest.bridge_plan_id]))
        if manifest.coverage_evaluation.evaluation_fingerprint != manifest.run.coverage_fingerprint:
            findings.append(finding("TEACHING_SESSION_COVERAGE_MISMATCH", [manifest.coverage_evaluation_id]))
        return findings


def _visible_manifests(actor):
    tenants = actor.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)
    return TeachingPreparationManifest.objects.filter(Q(intent__learner=actor) | Q(tenant_id__in=tenants)).select_related("run", "intent", "bridge_plan", "graph_version", "coverage_evaluation").distinct()


class CreateTeachingSessionService:
    def execute(self, *, preparation_manifest_id, actor, idempotency_key=""):
        manifest = _visible_manifests(actor).get(id=preparation_manifest_id)
        if actor.id != manifest.intent.learner_id:
            _govern(actor, manifest.tenant_id)
        authority_findings = ValidateTeachingAuthorityService().execute(intent=manifest.intent, manifest=manifest)
        if authority_findings:
            raise ValidationError(authority_findings[0].code, code=authority_findings[0].code)
        session_fp = fingerprint({"intent": str(manifest.intent_id), "manifest": manifest.manifest_fingerprint, "bridge_plan": manifest.bridge_plan.plan_fingerprint, "learner": str(manifest.intent.learner_id)})
        with transaction.atomic():
            existing = SelfStudyTeachingSession.objects.filter(intent=manifest.intent, idempotency_key=idempotency_key).first() if idempotency_key else None
            if existing:
                return existing, False
            session = SelfStudyTeachingSession.objects.create(
                tenant=manifest.tenant, learner=manifest.intent.learner, intent=manifest.intent, bridge_plan=manifest.bridge_plan,
                preparation_manifest=manifest, state=SelfStudyTeachingSessionState.PENDING, session_fingerprint=session_fp,
                privacy_policy_version=PRIVACY_POLICY_VERSION, disclosure_policy_version=DISCLOSURE_POLICY_VERSION,
                idempotency_key=idempotency_key or str(uuid.uuid4()),
            )
            packs = manifest.node_packs.select_related("bridge_node", "graph_node").order_by("topological_layer", "ordinal", "graph_node__stable_key")
            for pack in packs:
                permitted_roles = list(pack.resources.exclude(role="CONFLICT_WARNING").values_list("role", flat=True).distinct())
                ctx_fp = fingerprint({"session": str(session.id), "pack": pack.pack_fingerprint, "roles": sorted(permitted_roles)})
                TeachingSessionNode.objects.create(
                    session=session, bridge_node=pack.bridge_node, graph_node=pack.graph_node, teaching_pack=pack,
                    graph_version=manifest.graph_version, plan_ordinal=pack.ordinal, topological_layer=pack.topological_layer,
                    bridge_disposition=pack.bridge_disposition, permitted_roles=sorted(permitted_roles),
                    state=TeachingSessionNodeState.PENDING if pack.status == NodeTeachingPackStatus.READY else TeachingSessionNodeState.BLOCKED,
                    context_fingerprint=ctx_fp, transition_metadata={"source": "PI-6F.7"},
                )
            _after_commit("self_study.teaching_session.created", session_id=session.id, tenant_id=session.tenant_id, intent_id=session.intent_id)
        return session, True


class SelectCurrentTeachingNodeService:
    def execute(self, session):
        completed = set(session.nodes.filter(state=TeachingSessionNodeState.NODE_COMPLETE).values_list("bridge_node_id", flat=True))
        dependencies = session.bridge_plan.dependencies.select_related("predecessor_node", "successor_node")
        for node in session.nodes.select_related("teaching_pack", "graph_node").order_by("topological_layer", "plan_ordinal", "graph_node__stable_key"):
            if node.state in {TeachingSessionNodeState.NODE_COMPLETE, TeachingSessionNodeState.SKIPPED_BY_POLICY, TeachingSessionNodeState.CANCELLED}:
                continue
            if node.teaching_pack.status not in {NodeTeachingPackStatus.READY, NodeTeachingPackStatus.PUBLISHED, NodeTeachingPackStatus.ASSEMBLED}:
                continue
            required_predecessors = [dep.predecessor_node_id for dep in dependencies if dep.successor_node_id == node.bridge_node_id and dep.requirement_type == "MANDATORY"]
            if any(item not in completed for item in required_predecessors):
                continue
            return node
        return None


class StartTeachingSessionService:
    def execute(self, session_id, actor, expected_version):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().select_related("intent", "preparation_manifest", "bridge_plan").get(id=session_id)
            if actor.id != session.learner_id:
                _govern(actor, session.tenant_id)
            if session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            ensure_transition(session.state, SelfStudyTeachingSessionState.ACTIVE)
            node = SelectCurrentTeachingNodeService().execute(session)
            if not node:
                raise ValidationError("No eligible teaching node.", code="TEACHING_NODE_NOT_ELIGIBLE")
            node.state = TeachingSessionNodeState.ACTIVE
            node.save(update_fields=["state"])
            session.current_session_node = node
            session.state = SelfStudyTeachingSessionState.ACTIVE
            session.started_at = timezone.now()
            session.version += 1
            session.save()
            TeachingTransition.objects.create(session=session, source_state="PENDING", target_state=session.state, target_node=node, transition_type=TeachingTransitionType.START, actor=actor, authority="LEARNER", reason_code="TEACHING_SESSION_STARTED", expected_version=expected_version, transition_fingerprint=fingerprint({"session": str(session.id), "target": str(node.id), "type": "START", "version": expected_version}))
            transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["prepare_teaching_turn_task"]).prepare_teaching_turn_task.delay(str(session.id)))
            _after_commit("self_study.teaching_session.started", session_id=session.id, node_id=node.id, tenant_id=session.tenant_id)
            return session


class BuildTeachingContextService:
    def execute(self, session_id, learner_input=""):
        session = SelfStudyTeachingSession.objects.select_related("bridge_plan", "preparation_manifest__retrieval_manifest").get(id=session_id)
        node = session.current_session_node
        if not node:
            raise ValidationError("No current node.", code="TEACHING_NODE_NOT_CURRENT")
        assignments = [
            {
                "assignment_id": str(row.id), "role": row.role, "mapping_id": str(row.accepted_mapping_id),
                "evidence_unit_id": str(row.evidence_unit_id), "resource_id": str(row.resource_id),
                "citation": row.citation_snapshot, "citation_label": row.citation_snapshot.get("label", ""),
            }
            for row in TeachingPackResource.objects.filter(pack=node.teaching_pack).exclude(role="CONFLICT_WARNING").order_by("rank", "id")
        ]
        if not assignments:
            TeachingSessionFinding.objects.create(session=session, session_node=node, code="TEACHING_NO_ELIGIBLE_EVIDENCE", severity=TeachingFindingSeverity.BLOCKER, blocking=True, scope="NODE", affected_identities=[str(node.id)], details={}, policy_version=PROMPT_POLICY_VERSION)
            raise ValidationError("No eligible evidence.", code="TEACHING_NO_ELIGIBLE_EVIDENCE")
        prior = [
            {"id": str(row.id), "sequence_number": row.sequence_number, "actor": row.actor, "action": row.action}
            for row in session.turns.order_by("-sequence_number")[:8]
        ]
        payload = build_context_payload(session=session, session_node=node, learner_input=learner_input, prior_turns=prior, assignments=assignments, retrieval_manifest=session.preparation_manifest.retrieval_manifest)
        ctx_fp = fingerprint(payload)
        return TeachingContextSnapshot.objects.get_or_create(
            context_fingerprint=ctx_fp,
            defaults={
                "session": session, "session_node": node, "graph_version": node.graph_version,
                "bridge_plan_fingerprint": session.bridge_plan.plan_fingerprint,
                "preparation_fingerprint": session.preparation_manifest.manifest_fingerprint,
                "retrieval_fingerprint": session.preparation_manifest.retrieval_manifest.manifest_fingerprint,
                "permitted_roles": node.permitted_roles, "current_learner_input": learner_input,
                "prior_turn_references": prior, "retrieval_filters": session.preparation_manifest.retrieval_manifest.metadata_filters,
                "safety_policy_version": SAFETY_POLICY_VERSION, "disclosure_policy_version": DISCLOSURE_POLICY_VERSION,
                "model_version": MODEL_VERSION, "prompt_policy_version": PROMPT_POLICY_VERSION,
                "context_snapshot": payload,
            },
        )[0]


class GenerateTeachingTurnService:
    def execute(self, session_id, learner_input=""):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().select_related("preparation_manifest__retrieval_manifest", "bridge_plan").get(id=session_id)
            if session.state in {SelfStudyTeachingSessionState.STALE, SelfStudyTeachingSessionState.INVALIDATED, SelfStudyTeachingSessionState.BLOCKED}:
                raise ValidationError("Session cannot generate a turn.", code="TEACHING_SESSION_BLOCKED")
            if detect_prompt_injection(learner_input):
                TeachingSessionFinding.objects.create(session=session, session_node=session.current_session_node, code="TEACHING_PROMPT_INJECTION_DETECTED", severity=TeachingFindingSeverity.BLOCKER, blocking=True, scope="TURN", affected_identities=[], details={}, policy_version=PROMPT_POLICY_VERSION)
                session.state = SelfStudyTeachingSessionState.BLOCKED
                session.version += 1
                session.save()
                _after_commit("self_study.teaching_session.blocked", session_id=session.id, tenant_id=session.tenant_id)
                raise ValidationError("Prompt-injection pattern detected.", code="TEACHING_PROMPT_INJECTION_DETECTED")
            context = BuildTeachingContextService().execute(session.id, learner_input)
            assignments = context.context_snapshot["assignments"]
            roles = {item["role"] for item in assignments}
            action = select_action(has_learner_input=bool(learner_input.strip()), turn_count=session.turns.count(), node_type=session.current_session_node.graph_node.node_type, roles=roles)
            response = safe_teaching_text(action=action, node_title=session.current_session_node.graph_node.title, assignments=assignments, learner_input=learner_input)
            sequence = session.current_turn_sequence + 1
            payload = {"session": str(session.id), "node": str(session.current_session_node_id), "sequence": sequence, "action": action, "context": context.context_fingerprint, "response": response}
            turn = TeachingTurn.objects.create(
                session=session, session_node=session.current_session_node, sequence_number=sequence,
                actor=TeachingTurnActor.ABBOT, action=action, generated_response_reference=f"deterministic:{sequence}",
                context_snapshot=context, response_text=response, provider_version="deterministic",
                model_version=MODEL_VERSION, prompt_policy_version=PROMPT_POLICY_VERSION,
                generation_fingerprint=generation_fingerprint(payload), idempotency_key=f"generated:{sequence}",
                safety_status=TeachingSafetyStatus.SAFE,
            )
            resources = {str(row.id): row for row in TeachingPackResource.objects.filter(id__in=[item["assignment_id"] for item in assignments])}
            for item in assignments:
                resource = resources[item["assignment_id"]]
                citation_fp = fingerprint({"turn": str(turn.id), "assignment": str(resource.id), "citation": resource.citation_snapshot})
                TeachingTurnCitation.objects.create(turn=turn, teaching_pack_resource=resource, evidence_unit=resource.evidence_unit, resource=resource.resource, extraction_provenance={"source_block_id": str(resource.source_block_id), "source_input_id": str(resource.source_input_id)}, mapping_classification=resource.classification, teaching_role=resource.role, retrieval_record_identity=str(resource.id), citation=resource.citation_snapshot, citation_fingerprint=citation_fp)
            session.current_turn_sequence = sequence
            session.state = SelfStudyTeachingSessionState.AWAITING_LEARNER
            session.version += 1
            session.save()
            _after_commit("self_study.teaching_turn.generated", session_id=session.id, turn_id=turn.id, tenant_id=session.tenant_id)
            return turn


class RecordLearnerTurnService:
    def execute(self, session_id, actor, text, expected_version, idempotency_key):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().get(id=session_id)
            if actor.id != session.learner_id:
                raise PermissionDenied("TEACHING_SESSION_LEARNER_REQUIRED")
            if session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            if TeachingTurn.objects.filter(session=session, idempotency_key=idempotency_key).exists():
                return TeachingTurn.objects.get(session=session, idempotency_key=idempotency_key)
            if detect_prompt_injection(text):
                raise ValidationError("Prompt-injection pattern detected.", code="TEACHING_PROMPT_INJECTION_DETECTED")
            context = BuildTeachingContextService().execute(session.id, text)
            sequence = session.current_turn_sequence + 1
            turn = TeachingTurn.objects.create(session=session, session_node=session.current_session_node, sequence_number=sequence, actor=TeachingTurnActor.LEARNER, action=TeachingTurnAction.REFLECT, learner_input_reference=f"learner:{sequence}", context_snapshot=context, response_text=text, provider_version="learner", model_version="", prompt_policy_version=PROMPT_POLICY_VERSION, generation_fingerprint=fingerprint({"session": str(session.id), "sequence": sequence, "learner_text": text}), idempotency_key=idempotency_key)
            session.current_turn_sequence = sequence
            session.state = SelfStudyTeachingSessionState.ACTIVE
            session.version += 1
            session.save()
            transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["generate_teaching_turn_task"]).generate_teaching_turn_task.delay(str(session.id)))
            _after_commit("self_study.teaching_turn.recorded", session_id=session.id, turn_id=turn.id, tenant_id=session.tenant_id)
            return turn


class PauseTeachingSessionService:
    def execute(self, session_id, actor, expected_version, reason="LEARNER_PAUSED"):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().get(id=session_id)
            if actor.id != session.learner_id:
                _govern(actor, session.tenant_id)
            if session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            ensure_transition(session.state, SelfStudyTeachingSessionState.PAUSED)
            source = session.state
            session.state = SelfStudyTeachingSessionState.PAUSED
            session.paused_at = timezone.now()
            session.version += 1
            session.save()
            TeachingTransition.objects.create(session=session, source_state=source, target_state=session.state, source_node=session.current_session_node, target_node=session.current_session_node, transition_type=TeachingTransitionType.PAUSE, actor=actor, authority="LEARNER", reason_code=reason, expected_version=expected_version, transition_fingerprint=fingerprint({"session": str(session.id), "type": "PAUSE", "version": expected_version}))
            _after_commit("self_study.teaching_session.paused", session_id=session.id, tenant_id=session.tenant_id)
            return session


class ResumeTeachingSessionService:
    def execute(self, session_id, actor, expected_version):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().get(id=session_id)
            if actor.id != session.learner_id:
                _govern(actor, session.tenant_id)
            if session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            ensure_transition(session.state, SelfStudyTeachingSessionState.ACTIVE)
            session.state = SelfStudyTeachingSessionState.ACTIVE
            session.version += 1
            session.save()
            transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["prepare_teaching_turn_task"]).prepare_teaching_turn_task.delay(str(session.id)))
            _after_commit("self_study.teaching_session.resumed", session_id=session.id, tenant_id=session.tenant_id)
            return session


class RequestEvidenceEvaluationService:
    def execute(self, session_id, actor, expected_version):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().get(id=session_id)
            if actor.id != session.learner_id:
                raise PermissionDenied("TEACHING_SESSION_LEARNER_REQUIRED")
            if session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            session.state = SelfStudyTeachingSessionState.AWAITING_EVIDENCE
            session.current_session_node.state = TeachingSessionNodeState.AWAITING_EVIDENCE
            session.current_session_node.save(update_fields=["state"])
            session.version += 1
            session.save()
            TeachingSessionFinding.objects.create(session=session, session_node=session.current_session_node, code="TEACHING_EVIDENCE_EVALUATION_REQUIRED", severity=TeachingFindingSeverity.INFO, blocking=False, scope="NODE", affected_identities=[str(session.current_session_node_id)], details={"mastery_boundary": "no_mastery_awarded"}, policy_version=PROMPT_POLICY_VERSION)
            _after_commit("self_study.teaching_evidence.requested", session_id=session.id, node_id=session.current_session_node_id, tenant_id=session.tenant_id)
            return session


class CompleteTeachingNodeService:
    def execute(self, session_id, actor, expected_version, authority="POLICY"):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().get(id=session_id)
            if actor.id != session.learner_id:
                _govern(actor, session.tenant_id)
            if session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            node = session.current_session_node
            node.state = TeachingSessionNodeState.NODE_COMPLETE
            node.save(update_fields=["state"])
            session.state = SelfStudyTeachingSessionState.NODE_COMPLETE
            session.version += 1
            session.save()
            TeachingSessionFinding.objects.create(session=session, session_node=node, code="TEACHING_COMPLETION_NOT_MASTERY", severity=TeachingFindingSeverity.INFO, blocking=False, scope="SESSION", affected_identities=[str(node.id)], details={"mastery": "not_established"}, policy_version=PROMPT_POLICY_VERSION)
            _after_commit("self_study.teaching_session.node_completed", session_id=session.id, node_id=node.id, tenant_id=session.tenant_id)
            return session


class AdvanceTeachingSessionService:
    def execute(self, session_id, actor=None, expected_version=None):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().get(id=session_id)
            if expected_version and session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            node = SelectCurrentTeachingNodeService().execute(session)
            if not node:
                session.state = SelfStudyTeachingSessionState.COMPLETED
                session.completed_at = timezone.now()
                session.version += 1
                session.save()
                _after_commit("self_study.teaching_session.completed", session_id=session.id, tenant_id=session.tenant_id)
                return session
            node.state = TeachingSessionNodeState.ACTIVE
            node.save(update_fields=["state"])
            session.current_session_node = node
            session.state = SelfStudyTeachingSessionState.ACTIVE
            session.version += 1
            session.save()
            transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["prepare_teaching_turn_task"]).prepare_teaching_turn_task.delay(str(session.id)))
            _after_commit("self_study.teaching_session.advanced", session_id=session.id, node_id=node.id, tenant_id=session.tenant_id)
            return session


class RevisitTeachingNodeService:
    def execute(self, session_id, actor, bridge_node_id, expected_version):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().get(id=session_id)
            if actor.id != session.learner_id:
                raise PermissionDenied("TEACHING_SESSION_LEARNER_REQUIRED")
            if session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            node = session.nodes.get(bridge_node_id=bridge_node_id)
            session.current_session_node = node
            session.state = SelfStudyTeachingSessionState.ACTIVE
            session.version += 1
            session.save()
            TeachingSessionFinding.objects.create(session=session, session_node=node, code="TEACHING_REVISIT_REQUESTED", severity=TeachingFindingSeverity.INFO, blocking=False, scope="NODE", affected_identities=[str(node.id)], details={}, policy_version=PROMPT_POLICY_VERSION)
            _after_commit("self_study.teaching_session.advanced", session_id=session.id, node_id=node.id, tenant_id=session.tenant_id)
            return session


class InvalidateTeachingSessionService:
    def execute(self, session_id, actor, expected_version, reason="TEACHING_SESSION_INVALIDATED"):
        with transaction.atomic():
            session = SelfStudyTeachingSession.objects.select_for_update().get(id=session_id)
            _govern(actor, session.tenant_id)
            if session.version != expected_version:
                raise ValidationError("Session version changed.", code="TEACHING_SESSION_VERSION_CONFLICT")
            session.state = SelfStudyTeachingSessionState.INVALIDATED
            session.version += 1
            session.save()
            _audit_after_commit(actor=actor, institution=session.tenant, action="self_study.teaching_session.invalidated", session=session, metadata={"reason": reason})
            _after_commit("self_study.teaching_session.invalidated", session_id=session.id, tenant_id=session.tenant_id)
            return session


class MarkTeachingSessionsStaleService:
    def execute(self, *, tenant_id, reason, bridge_plan_id=None, preparation_manifest_id=None):
        filters = {"tenant_id": tenant_id}
        if bridge_plan_id:
            filters["bridge_plan_id"] = bridge_plan_id
        if preparation_manifest_id:
            filters["preparation_manifest_id"] = preparation_manifest_id
        with transaction.atomic():
            sessions = list(SelfStudyTeachingSession.objects.select_for_update().filter(**filters).exclude(state__in=[SelfStudyTeachingSessionState.STALE, SelfStudyTeachingSessionState.INVALIDATED, SelfStudyTeachingSessionState.COMPLETED, SelfStudyTeachingSessionState.CANCELLED]))
            for session in sessions:
                session.state = SelfStudyTeachingSessionState.STALE
                session.version += 1
                session.save(update_fields=["state", "version"])
                TeachingSessionFinding.objects.create(session=session, code="TEACHING_SESSION_STALE", severity=TeachingFindingSeverity.BLOCKER, blocking=True, scope="SESSION", affected_identities=[], details={"reason": reason}, policy_version=PROMPT_POLICY_VERSION)
                _after_commit("self_study.teaching_session.stale", session_id=session.id, tenant_id=session.tenant_id, reason=reason)
            return sessions


class GetCurrentTeachingContextService:
    def execute(self, session_id, actor):
        session = SelfStudyTeachingSession.objects.select_related("current_session_node__graph_node").get(id=session_id)
        if actor.id != session.learner_id:
            _govern(actor, session.tenant_id)
        snapshot = session.context_snapshots.order_by("-created_at").first()
        return {"session_id": str(session.id), "state": session.state, "current_node_id": str(session.current_session_node_id) if session.current_session_node_id else None, "current_node_title": session.current_session_node.graph_node.title if session.current_session_node_id else None, "context": snapshot.context_snapshot if snapshot else None}


class GetTeachingSessionHandoffService:
    def execute(self, session_id, actor):
        session = SelfStudyTeachingSession.objects.select_related("preparation_manifest__retrieval_manifest", "bridge_plan").get(id=session_id)
        if actor.id != session.learner_id:
            _govern(actor, session.tenant_id)
        if session.state in {SelfStudyTeachingSessionState.STALE, SelfStudyTeachingSessionState.INVALIDATED, SelfStudyTeachingSessionState.BLOCKED}:
            raise ValidationError("Session cannot hand off.", code="TEACHING_SESSION_STALE")
        prep = GetTeachingOrchestrationHandoffService().execute(str(session.intent_id), actor, str(session.bridge_plan_id))
        return {
            "session_id": str(session.id), "session_fingerprint": session.session_fingerprint, "state": session.state,
            "current_node_id": str(session.current_session_node_id) if session.current_session_node_id else None,
            "current_turn_sequence": session.current_turn_sequence, "preparation": prep,
            "turns": list(session.turns.order_by("sequence_number").values("id", "sequence_number", "actor", "action", "safety_status", "created_at")),
        }
