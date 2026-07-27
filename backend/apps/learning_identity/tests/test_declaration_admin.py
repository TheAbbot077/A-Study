from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.learning_identity.admin import LearningIdentityDeclarationSynchronizationAdmin
from apps.learning_identity.domain.models import LearningIdentityDeclarationSynchronization


class DeclarationSynchronizationAdminTests(TestCase):
    def test_receipt_admin_is_registered_read_only_and_hides_payload_fingerprint(self):
        model_admin = admin.site._registry[LearningIdentityDeclarationSynchronization]
        self.assertIsInstance(model_admin, LearningIdentityDeclarationSynchronizationAdmin)
        request = RequestFactory().get("/")
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertIn("payload_fingerprint", model_admin.exclude)
