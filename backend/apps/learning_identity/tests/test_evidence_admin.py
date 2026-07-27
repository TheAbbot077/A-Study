from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.learning_identity.admin import LearningIdentityEvidenceLinkAdmin
from apps.learning_identity.domain.models import LearningIdentityEvidenceLink
from apps.users.domain.models import User


class EvidenceAdminTests(TestCase):
    def test_evidence_link_admin_is_registered_and_inspection_only(self):
        model_admin = admin.site._registry[LearningIdentityEvidenceLink]
        self.assertIsInstance(model_admin, LearningIdentityEvidenceLinkAdmin)
        request = RequestFactory().get("/")
        request.user = User.objects.create_superuser(email="admin@example.com", password="test")
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertIn("source_identifier", model_admin.readonly_fields)
        self.assertIn("authority_class", model_admin.readonly_fields)
