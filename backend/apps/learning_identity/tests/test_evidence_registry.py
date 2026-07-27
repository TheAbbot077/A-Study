from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.learning_identity.domain.enums import EvidenceSourceDomain, EvidenceSourceType
from apps.learning_identity.infrastructure.evidence_resolvers import (
    EvidenceSourceResolverRegistry,
    LearningIdentityDeclarationResolver,
    build_default_evidence_resolver_registry,
)


class EvidenceResolverRegistryTests(TestCase):
    def test_default_registry_supports_minimal_real_sources(self):
        registry = build_default_evidence_resolver_registry()
        self.assertIsNotNone(registry._resolvers[(EvidenceSourceDomain.LEARNING_IDENTITY, EvidenceSourceType.LEARNER_DECLARATION)])
        self.assertIsNotNone(registry._resolvers[(EvidenceSourceDomain.INSTITUTION, EvidenceSourceType.INSTITUTIONAL_MEMBERSHIP)])
        self.assertIsNotNone(registry._resolvers[(EvidenceSourceDomain.SELF_STUDY, EvidenceSourceType.ONBOARDING_CONTEXT)])

    def test_duplicate_registration_and_unsupported_source_fail_closed(self):
        registry = EvidenceSourceResolverRegistry()
        registry.register(
            source_domain=EvidenceSourceDomain.LEARNING_IDENTITY,
            source_type=EvidenceSourceType.LEARNER_DECLARATION,
            resolver=LearningIdentityDeclarationResolver(),
        )
        with self.assertRaises(ValidationError):
            registry.register(
                source_domain=EvidenceSourceDomain.LEARNING_IDENTITY,
                source_type=EvidenceSourceType.LEARNER_DECLARATION,
                resolver=LearningIdentityDeclarationResolver(),
            )
        with self.assertRaisesMessage(ValidationError, "Unsupported evidence source type"):
            registry.resolve(
                source_domain=EvidenceSourceDomain.ASSESSMENT,
                source_type=EvidenceSourceType.ASSESSMENT_EVIDENCE,
                source_identifier="missing",
                learner_id="learner",
                tenant_id="tenant",
            )
