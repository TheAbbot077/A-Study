from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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


class AcademicApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@example.com", password="secret")
        self.client.force_authenticate(user=self.user)
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
            requested_by=self.user,
        )

    def test_subject_list_endpoint(self):
        response = self.client.get(reverse("academic-subject-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["code"], "MATH")

    def test_subject_create_endpoint_delegates_to_service(self):
        payload = {"institution": str(self.institution.id), "code": "SCI", "name": "Science"}
        created_subject = Subject(institution=self.institution, code="SCI", name="Science")

        with patch("apps.academic.api.views.AcademicStructureService.create_subject", return_value=created_subject) as create_subject:
            response = self.client.post(reverse("academic-subject-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        create_subject.assert_called_once()
        self.assertEqual(response.data["code"], "SCI")

    def test_subject_archive_endpoint(self):
        with patch("apps.academic.api.views.AcademicStructureService.archive_subject", return_value=self.subject) as archive_subject:
            response = self.client.post(reverse("academic-subject-archive", args=[self.subject.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        archive_subject.assert_called_once_with(self.subject)

    def test_curriculum_list_endpoint(self):
        response = self.client.get(reverse("academic-curriculum-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], "Core Mathematics")

    def test_curriculum_create_endpoint(self):
        payload = {
            "subject": str(self.subject.id),
            "institution": str(self.institution.id),
            "name": "Advanced Mathematics",
            "version": "2.0",
        }
        created_curriculum = Curriculum(
            subject=self.subject,
            institution=self.institution,
            name="Advanced Mathematics",
            version="2.0",
        )

        with patch("apps.academic.api.views.CurriculumService.create_curriculum", return_value=created_curriculum) as create_curriculum:
            response = self.client.post(reverse("academic-curriculum-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        create_curriculum.assert_called_once()
        self.assertEqual(response.data["name"], "Advanced Mathematics")

    def test_curriculum_unit_list_endpoint(self):
        response = self.client.get(reverse("academic-curriculum-unit-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["title"], "Algebra")

    def test_learning_resource_list_endpoint(self):
        response = self.client.get(reverse("academic-learning-resource-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["title"], "Algebra Guide")

    def test_content_section_list_endpoint(self):
        response = self.client.get(reverse("academic-content-section-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["title"], "Linear Equations")

    def test_content_concept_list_endpoint(self):
        response = self.client.get(reverse("academic-content-concept-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["title"], "Solving for x")

    def test_section_submit_approve_reject_review_actions(self):
        with patch("apps.academic.api.views.ContentReviewService.submit_section_for_review", return_value=self.section) as submit:
            submit_response = self.client.post(reverse("academic-content-section-submit-for-review", args=[self.section.id]))
        with patch("apps.academic.api.views.ContentReviewService.approve_section", return_value=self.section) as approve:
            approve_response = self.client.post(reverse("academic-content-section-approve", args=[self.section.id]))
        with patch("apps.academic.api.views.ContentReviewService.reject_section", return_value=self.section) as reject:
            reject_response = self.client.post(reverse("academic-content-section-reject", args=[self.section.id]))

        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        submit.assert_called_once()
        approve.assert_called_once()
        reject.assert_called_once()

    def test_concept_submit_approve_reject_review_actions(self):
        with patch("apps.academic.api.views.ContentReviewService.submit_concept_for_review", return_value=self.concept) as submit:
            submit_response = self.client.post(reverse("academic-content-concept-submit-for-review", args=[self.concept.id]))
        with patch("apps.academic.api.views.ContentReviewService.approve_concept", return_value=self.concept) as approve:
            approve_response = self.client.post(reverse("academic-content-concept-approve", args=[self.concept.id]))
        with patch("apps.academic.api.views.ContentReviewService.reject_concept", return_value=self.concept) as reject:
            reject_response = self.client.post(reverse("academic-content-concept-reject", args=[self.concept.id]))

        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        submit.assert_called_once()
        approve.assert_called_once()
        reject.assert_called_once()

    def test_quality_marking_endpoints(self):
        section_payload = {"quality_status": ContentSection.QualityStatus.HIGH, "notes": "Strong"}
        concept_payload = {"quality_status": ContentConcept.QualityStatus.ACCEPTABLE, "notes": "Acceptable"}

        with patch("apps.academic.api.views.ContentReviewService.mark_section_quality", return_value=self.section) as mark_section:
            section_response = self.client.post(
                reverse("academic-content-section-mark-quality", args=[self.section.id]),
                section_payload,
                format="json",
            )
        with patch("apps.academic.api.views.ContentReviewService.mark_concept_quality", return_value=self.concept) as mark_concept:
            concept_response = self.client.post(
                reverse("academic-content-concept-mark-quality", args=[self.concept.id]),
                concept_payload,
                format="json",
            )

        self.assertEqual(section_response.status_code, status.HTTP_200_OK)
        self.assertEqual(concept_response.status_code, status.HTTP_200_OK)
        mark_section.assert_called_once()
        mark_concept.assert_called_once()

    def test_ingestion_job_list_endpoint(self):
        response = self.client.get(reverse("academic-ingestion-job-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["learning_resource"], str(self.resource.id))

    def test_ingestion_job_lifecycle_actions(self):
        with patch("apps.academic.api.views.ResourceIngestionService.start_job", return_value=self.job) as start:
            start_response = self.client.post(reverse("academic-ingestion-job-start", args=[self.job.id]))
        with patch("apps.academic.api.views.ResourceIngestionService.complete_job", return_value=self.job) as complete:
            complete_response = self.client.post(reverse("academic-ingestion-job-complete", args=[self.job.id]))
        with patch("apps.academic.api.views.ResourceIngestionService.fail_job", return_value=self.job) as fail:
            fail_response = self.client.post(
                reverse("academic-ingestion-job-fail", args=[self.job.id]),
                {"error_message": "Import failed"},
                format="json",
            )
        with patch("apps.academic.api.views.ResourceIngestionService.cancel_job", return_value=self.job) as cancel:
            cancel_response = self.client.post(reverse("academic-ingestion-job-cancel", args=[self.job.id]))

        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        self.assertEqual(fail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        start.assert_called_once()
        complete.assert_called_once()
        fail.assert_called_once()
        cancel.assert_called_once()

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("academic-subject-list"))

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
