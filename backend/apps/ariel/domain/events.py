"""
Ariel domain events. Identifier-only payloads. Idempotent.
"""


class ArielIdentityCreated:
    event_type = "ariel.identity.created"
    version = 1

    def __init__(self, identity_id, learner_id, constitution_version):
        self.identity_id = identity_id
        self.learner_id = learner_id
        self.constitution_version = constitution_version

    def payload(self):
        return {
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
            "constitution_version": self.constitution_version,
        }


class ArielActivated:
    event_type = "ariel.activated"
    version = 1

    def __init__(self, identity_id, learner_id):
        self.identity_id = identity_id
        self.learner_id = learner_id

    def payload(self):
        return {"identity_id": str(self.identity_id), "learner_id": str(self.learner_id)}


class TeachingSessionStarted:
    event_type = "ariel.teaching_session.started"
    version = 1

    def __init__(self, session_id, identity_id, learner_id, constitution_version):
        self.session_id = session_id
        self.identity_id = identity_id
        self.learner_id = learner_id
        self.constitution_version = constitution_version

    def payload(self):
        return {
            "session_id": str(self.session_id),
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
            "constitution_version": self.constitution_version,
        }


class LearnerTaughtAriel:
    event_type = "ariel.learner_taught"
    version = 1

    def __init__(self, session_id, identity_id, learner_id, turn_id):
        self.session_id = session_id
        self.identity_id = identity_id
        self.learner_id = learner_id
        self.turn_id = turn_id

    def payload(self):
        return {
            "session_id": str(self.session_id),
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
            "turn_id": str(self.turn_id),
        }


class KnowledgeCreated:
    event_type = "ariel.knowledge.created"
    version = 1

    def __init__(self, knowledge_id, identity_id, learner_id, session_id, turn_id):
        self.knowledge_id = knowledge_id
        self.identity_id = identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.turn_id = turn_id

    def payload(self):
        return {
            "knowledge_id": str(self.knowledge_id),
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "turn_id": str(self.turn_id),
        }


class MemoryReinforced:
    event_type = "ariel.memory.reinforced"
    version = 1

    def __init__(self, knowledge_id, identity_id, learner_id):
        self.knowledge_id = knowledge_id
        self.identity_id = identity_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "knowledge_id": str(self.knowledge_id),
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
        }


class MemoryCorrected:
    event_type = "ariel.memory.corrected"
    version = 1

    def __init__(self, old_knowledge_id, new_knowledge_id, identity_id, learner_id):
        self.old_knowledge_id = old_knowledge_id
        self.new_knowledge_id = new_knowledge_id
        self.identity_id = identity_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "old_knowledge_id": str(self.old_knowledge_id),
            "new_knowledge_id": str(self.new_knowledge_id),
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
        }


class MemoryForgotten:
    event_type = "ariel.memory.forgotten"
    version = 1

    def __init__(self, knowledge_id, identity_id, learner_id):
        self.knowledge_id = knowledge_id
        self.identity_id = identity_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "knowledge_id": str(self.knowledge_id),
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
        }


class MemoryConflicted:
    event_type = "ariel.memory.conflicted"
    version = 1

    def __init__(self, knowledge_id, conflicting_knowledge_id, identity_id, learner_id):
        self.knowledge_id = knowledge_id
        self.conflicting_knowledge_id = conflicting_knowledge_id
        self.identity_id = identity_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "knowledge_id": str(self.knowledge_id),
            "conflicting_knowledge_id": str(self.conflicting_knowledge_id),
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
        }


class MemoryRetracted:
    event_type = "ariel.memory.retracted"
    version = 1

    def __init__(self, knowledge_id, identity_id, learner_id):
        self.knowledge_id = knowledge_id
        self.identity_id = identity_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "knowledge_id": str(self.knowledge_id),
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
        }


class ArielReset:
    event_type = "ariel.reset"
    version = 1

    def __init__(self, identity_id, learner_id):
        self.identity_id = identity_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "identity_id": str(self.identity_id),
            "learner_id": str(self.learner_id),
        }


class ArielTeachBackStarted:
    event_type = "ariel.teach_back.started"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id, source_memory_id=None):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.source_memory_id = source_memory_id

    def payload(self):
        payload = {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }
        if self.source_memory_id is not None:
            payload["source_memory_id"] = str(self.source_memory_id)
        return payload


class ArielTeachBackPresented:
    event_type = "ariel.teach_back.presented"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id

    def payload(self):
        return {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }


class ArielTeachBackResponded:
    event_type = "ariel.teach_back.responded"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id, learner_response_turn_id=None):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.learner_response_turn_id = learner_response_turn_id

    def payload(self):
        payload = {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }
        if self.learner_response_turn_id is not None:
            payload["learner_response_turn_id"] = str(self.learner_response_turn_id)
        return payload


class ArielTeachBackSkipped:
    event_type = "ariel.teach_back.skipped"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id

    def payload(self):
        return {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }


class ArielTeachBackCancelled:
    event_type = "ariel.teach_back.cancelled"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id

    def payload(self):
        return {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }


class ArielTeachingTransformationRequested:
    event_type = "ariel.teaching_transformation.requested"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id, artefact_id=None):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.artefact_id = artefact_id

    def payload(self):
        payload = {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }
        if self.artefact_id is not None:
            payload["artefact_id"] = str(self.artefact_id)
        return payload


class ArielTeachingTransformationCompleted:
    event_type = "ariel.teaching_transformation.completed"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id, artefact_id=None):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.artefact_id = artefact_id

    def payload(self):
        payload = {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }
        if self.artefact_id is not None:
            payload["artefact_id"] = str(self.artefact_id)
        return payload


class ArielDelayedReteachingRequested:
    event_type = "ariel.delayed_reteaching.requested"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id, source_memory_id=None):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.source_memory_id = source_memory_id

    def payload(self):
        payload = {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }
        if self.source_memory_id is not None:
            payload["source_memory_id"] = str(self.source_memory_id)
        return payload


class ArielMisunderstandingPresented:
    event_type = "ariel.misunderstanding.presented"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id, source_memory_id=None):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.source_memory_id = source_memory_id

    def payload(self):
        payload = {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }
        if self.source_memory_id is not None:
            payload["source_memory_id"] = str(self.source_memory_id)
        return payload


class ArielMisunderstandingCorrected:
    event_type = "ariel.misunderstanding.corrected"
    version = 1

    def __init__(self, ariel_identity_id, learner_id, session_id, interaction_id, source_memory_id=None):
        self.ariel_identity_id = ariel_identity_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.source_memory_id = source_memory_id

    def payload(self):
        payload = {
            "ariel_identity_id": str(self.ariel_identity_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id),
            "interaction_id": str(self.interaction_id),
        }
        if self.source_memory_id is not None:
            payload["source_memory_id"] = str(self.source_memory_id)
        return payload
