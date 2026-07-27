from django.test import SimpleTestCase

from apps.core.events import default_event_registry


class LearningIdentityEventRegistryTests(SimpleTestCase):
    def test_learning_identity_events_are_registered(self):
        for event_name in [
            "learning_identity.profile.created",
            "learning_identity.profile_version.created",
            "learning_identity.attribute.declared",
            "learning_identity.profile_version.published",
            "learning_identity.profile_version.superseded",
            "learning_identity.profile.restricted",
            "learning_identity.profile.archived",
            "learning_identity.evidence.linked",
            "learning_identity.evidence.withdrawn",
            "learning_identity.evidence.invalidated",
            "learning_identity.evidence.marked_stale",
            "learning_identity.evidence.superseded",
            "learning_identity.attribute.contradicted",
            "learning_identity.profile.provenance_review_required",
            "learning_identity.profile.restricted_by_provenance",
            "learning_identity.profile_version.provenance_evaluated",
            "learning_identity.declarations.synchronized",
            "learning_identity.declaration.added",
            "learning_identity.declaration.updated",
            "learning_identity.declaration.cleared",
            "learning_identity.declaration.unchanged",
            "learning_identity.onboarding_sync.blocked",
            "learning_identity.onboarding_sync.failed",
            "learning_identity.profile_version.published_from_onboarding",
            "learning_identity.observation.synchronized",
            "learning_identity.observation.unchanged",
            "learning_identity.observation.rejected",
            "learning_identity.observation.contested",
            "learning_identity.declaration.withdrawn",
            "learning_identity.preference.selected",
            "learning_identity.preference.updated",
            "learning_identity.preference.withdrawn",
        ]:
            self.assertEqual(default_event_registry.get_subscribers(event_name), [])
