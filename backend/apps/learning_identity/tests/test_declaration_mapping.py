from datetime import date

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.learning_identity.domain.declaration_mapping import (
    OnboardingDeclarationMapping,
    OnboardingDeclarationMappingRegistry,
    build_default_onboarding_declaration_mapping_registry,
)
from apps.learning_identity.domain.enums import LearningAttributeType


class DeclarationMappingTests(SimpleTestCase):
    def test_supported_fields_normalize_deterministically(self):
        registry = build_default_onboarding_declaration_mapping_registry()
        self.assertEqual(registry.get("topic_query").normalize("  Pass Biology  "), "Pass Biology")
        self.assertEqual(registry.get("qualification_query").normalize(" Cambridge International A Level "), "Cambridge International A Level")
        self.assertEqual(registry.get("target_date").normalize(date(2027, 5, 1)), "2027-05-01")
        self.assertEqual(registry.get("weekly_study_minutes").normalize("300"), 300)

    def test_semantic_equality_uses_type_normalization(self):
        registry = build_default_onboarding_declaration_mapping_registry()
        self.assertTrue(registry.get("topic_query").equivalent("  Pass Biology  ", "Pass Biology"))
        self.assertTrue(registry.get("weekly_study_minutes").equivalent("300", 300))
        self.assertTrue(registry.get("target_date").equivalent(date(2027, 5, 1), "2027-05-01"))

    def test_unsupported_and_duplicate_mappings_fail_closed(self):
        registry = build_default_onboarding_declaration_mapping_registry()
        with self.assertRaises(ValidationError):
            registry.get("conversation_language_guess")
        with self.assertRaises(ValidationError):
            registry.register(
                OnboardingDeclarationMapping(
                    source_field="topic_query",
                    target_attribute_type=LearningAttributeType.STUDY_GOAL,
                    supported_source_schema_versions=(1,),
                    normalizer=str,
                )
            )

    def test_prohibited_learning_style_language_is_rejected(self):
        registry = build_default_onboarding_declaration_mapping_registry()
        with self.assertRaises(ValidationError):
            registry.get("topic_query").normalize("I am a visual learner")
