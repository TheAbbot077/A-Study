from unittest.mock import Mock, patch

from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from apps.academic.domain.models import (
    ContentConcept,
    ContentSection,
    Curriculum,
    CurriculumUnit,
    LearningResource,
    ResourceIngestionJob,
    Subject,
)
from apps.users.domain.models import Institution, User


class AcademicAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(email="admin@example.com", password="secret")
        self.client.force_login(self.superuser)
        self.institution = Institution.objects.create(name="Demo School", slug="demo-school")
        self.subject = Subject.objects.create(institution=self.institution, code="MATH", name="Mathematics")
        self.curriculum = Curriculum.objects.create(
            subject=self.subject,
            institution=self.institution,
            name="Core Mathematics",
            version="1.0",
        )
        self.unit = CurriculumUnit.objects.create(curriculum=self.curriculum, title="Algebra", sequence_number=1)
        self.resource = LearningResource.objects.create(
            institution=self.institution,
            subject=self.subject,
            curriculum=self.curriculum,
            curriculum_unit=self.unit,
            title="Algebra Guide",
        )
        self.section = ContentSection.objects.create(
            learning_resource=self.resource,
            title="Linear Equations",
            sequence_number=1,
        )
        self.concept = ContentConcept.objects.create(
            content_section=self.section,
            title="Solving for x",
            sequence_number=1,
        )
        self.job = ResourceIngestionJob.objects.create(
            learning_resource=self.resource,
            requested_by=self.superuser,
        )

    def test_academic_models_are_registered_in_admin(self):
        for model in [
            Subject,
            Curriculum,
            CurriculumUnit,
            LearningResource,
            ContentSection,
            ContentConcept,
            ResourceIngestionJob,
        ]:
            self.assertIn(model, admin.site._registry)

    def test_admin_list_pages_are_accessible_to_superuser(self):
        for model_name in [
            "subject",
            "curriculum",
            "curriculumunit",
            "learningresource",
            "contentsection",
            "contentconcept",
            "resourceingestionjob",
        ]:
            response = self.client.get(reverse(f"admin:academic_{model_name}_changelist"))

            self.assertEqual(response.status_code, 200)

    def test_archive_admin_action_applies_expected_archive_behavior(self):
        response = self.client.post(
            reverse("admin:academic_subject_changelist"),
            {
                "action": "archive_selected_subjects",
                "_selected_action": [str(self.subject.id)],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.subject.refresh_from_db()
        self.assertFalse(self.subject.is_active)

    def test_section_review_actions_update_review_status(self):
        self._post_admin_action(
            "admin:academic_contentsection_changelist",
            "submit_selected_sections_for_review",
            self.section.id,
        )
        self.section.refresh_from_db()
        self.assertEqual(self.section.review_status, ContentSection.ReviewStatus.IN_REVIEW)

        self._post_admin_action(
            "admin:academic_contentsection_changelist",
            "approve_selected_sections",
            self.section.id,
        )
        self.section.refresh_from_db()
        self.assertEqual(self.section.review_status, ContentSection.ReviewStatus.APPROVED)

        self._post_admin_action(
            "admin:academic_contentsection_changelist",
            "reject_selected_sections",
            self.section.id,
        )
        self.section.refresh_from_db()
        self.assertEqual(self.section.review_status, ContentSection.ReviewStatus.REJECTED)

    def test_concept_review_actions_update_review_status(self):
        self._post_admin_action(
            "admin:academic_contentconcept_changelist",
            "submit_selected_concepts_for_review",
            self.concept.id,
        )
        self.concept.refresh_from_db()
        self.assertEqual(self.concept.review_status, ContentConcept.ReviewStatus.IN_REVIEW)

        self._post_admin_action(
            "admin:academic_contentconcept_changelist",
            "approve_selected_concepts",
            self.concept.id,
        )
        self.concept.refresh_from_db()
        self.assertEqual(self.concept.review_status, ContentConcept.ReviewStatus.APPROVED)

        self._post_admin_action(
            "admin:academic_contentconcept_changelist",
            "reject_selected_concepts",
            self.concept.id,
        )
        self.concept.refresh_from_db()
        self.assertEqual(self.concept.review_status, ContentConcept.ReviewStatus.REJECTED)

    def test_readonly_fields_are_configured_where_expected(self):
        section_admin = admin.site._registry[ContentSection]
        concept_admin = admin.site._registry[ContentConcept]
        job_admin = admin.site._registry[ResourceIngestionJob]

        for field_name in ["id", "created_at", "updated_at", "approved_at"]:
            self.assertIn(field_name, section_admin.readonly_fields)
            self.assertIn(field_name, concept_admin.readonly_fields)

        for field_name in ["id", "created_at", "updated_at", "started_at", "completed_at"]:
            self.assertIn(field_name, job_admin.readonly_fields)

    def test_admin_save_model_delegates_subject_updates_to_service(self):
        subject_admin = admin.site._registry[Subject]
        form = Mock(cleaned_data={"name": "Updated Mathematics"})

        with patch("apps.academic.admin.AcademicStructureService.update_subject", return_value=self.subject) as update_subject:
            subject_admin.save_model(Mock(), self.subject, form, change=True)

        update_subject.assert_called_once_with(self.subject, name="Updated Mathematics")

    def test_admin_save_model_delegates_section_creation_to_service(self):
        section_admin = admin.site._registry[ContentSection]
        form = Mock(
            cleaned_data={
                "learning_resource": self.resource,
                "title": "Quadratics",
                "description": "",
                "sequence_number": 2,
                "is_active": True,
            }
        )
        section = ContentSection()
        created_section = ContentSection(id=self.section.id, learning_resource=self.resource, title="Quadratics", sequence_number=2)

        with patch("apps.academic.admin.ManualAuthoringService.create_section", return_value=created_section) as create_section:
            section_admin.save_model(Mock(), section, form, change=False)

        create_section.assert_called_once_with(**form.cleaned_data)
        self.assertEqual(section.id, created_section.id)

    def test_ingestion_job_admin_does_not_allow_direct_add_or_change_mutation(self):
        job_admin = admin.site._registry[ResourceIngestionJob]

        self.assertFalse(job_admin.has_add_permission(Mock()))
        self.assertFalse(job_admin.has_delete_permission(Mock(), self.job))

        readonly_fields = job_admin.get_readonly_fields(Mock(), self.job)
        for field in ResourceIngestionJob._meta.fields:
            self.assertIn(field.name, readonly_fields)

    def test_academic_admin_models_disable_direct_deletes(self):
        for model in [
            Subject,
            Curriculum,
            CurriculumUnit,
            LearningResource,
            ContentSection,
            ContentConcept,
            ResourceIngestionJob,
        ]:
            model_admin = admin.site._registry[model]

            self.assertFalse(model_admin.has_delete_permission(Mock()))

    def _post_admin_action(self, admin_url_name: str, action: str, object_id):
        response = self.client.post(
            reverse(admin_url_name),
            {
                "action": action,
                "_selected_action": [str(object_id)],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        return response
