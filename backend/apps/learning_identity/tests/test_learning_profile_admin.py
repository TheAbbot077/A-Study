from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.learning_identity.admin import LearnerLearningProfileAdmin, LearningIdentityAttributeAdmin, LearningProfileVersionAdmin
from apps.learning_identity.domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningProfileVersion
from apps.users.domain.models import Institution, User


class LearningProfileAdminTests(TestCase):
    def test_models_are_registered_inspection_only(self):
        self.assertIsInstance(admin.site._registry[LearnerLearningProfile], LearnerLearningProfileAdmin)
        self.assertIsInstance(admin.site._registry[LearningProfileVersion], LearningProfileVersionAdmin)
        self.assertIsInstance(admin.site._registry[LearningIdentityAttribute], LearningIdentityAttributeAdmin)

        request = RequestFactory().get("/")
        request.user = User.objects.create_superuser(email="admin@example.com", password="test")
        model_admin = admin.site._registry[LearnerLearningProfile]
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))

    def test_admin_readonly_fields_include_lifecycle_authority(self):
        model_admin = admin.site._registry[LearnerLearningProfile]
        readonly = set(model_admin.readonly_fields)
        self.assertTrue({"tenant", "learner", "status", "current_version", "version"}.issubset(readonly))
