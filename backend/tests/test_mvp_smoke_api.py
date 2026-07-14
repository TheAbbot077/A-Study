from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academic.domain.models import ContentConcept, ContentSection, LearningResource, Subject
from apps.storage.domain.models import StoredFile
from apps.users.domain.models import Institution, InstitutionMembership, InstitutionRole, User


class MvpSmokeApiTests(APITestCase):
    def setUp(self):
        self.password = "secret12345"
        self.user = User.objects.create_user(email="smoke@example.com", password=self.password)
        self.institution = Institution.objects.create(name="Smoke School", slug="smoke-school")
        InstitutionMembership.objects.create(
            user=self.user,
            institution=self.institution,
            role=InstitutionRole.STUDENT,
            is_active=True,
        )
        self.subject = Subject.objects.create(
            institution=self.institution,
            code="BIO101",
            name="Biology",
            description="Smoke subject",
        )
        self.stored_file = StoredFile.objects.create(
            original_filename="smoke.pdf",
            stored_filename="smoke.pdf",
            content_type="application/pdf",
            size_bytes=512,
            checksum="smoke-checksum",
            provider="local",
        )
        self.resource = LearningResource.objects.create(
            institution=self.institution,
            subject=self.subject,
            stored_file=self.stored_file,
            title="Unit 1 Notes",
            description="Smoke resource",
            resource_type=LearningResource.ResourceType.NOTES,
            status=LearningResource.Status.ACTIVE,
            source_label="smoke.pdf",
        )
        self.section = ContentSection.objects.create(
            learning_resource=self.resource,
            title="Chapter 1",
            description="Smoke section",
            sequence_number=1,
            review_status=ContentSection.ReviewStatus.APPROVED,
            quality_status=ContentSection.QualityStatus.ACCEPTABLE,
        )
        self.concept = ContentConcept.objects.create(
            content_section=self.section,
            title="Cell Structure",
            description="Smoke concept",
            learning_objective="Explain organelles",
            sequence_number=1,
            review_status=ContentConcept.ReviewStatus.APPROVED,
            quality_status=ContentConcept.QualityStatus.ACCEPTABLE,
        )

    def authenticate(self):
        self.client.force_authenticate(self.user)

    def assertNotServerError(self, response, allowed_statuses):
        self.assertIn(
            response.status_code,
            allowed_statuses,
            msg=f"Expected one of {allowed_statuses}, got {response.status_code} with body {getattr(response, 'data', response.content)}",
        )

    def test_authentication_routes_smoke(self):
        unauthenticated_subjects = self.client.get("/api/academic/subjects/")
        self.assertIn(
            unauthenticated_subjects.status_code,
            {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN},
        )

        register_response = self.client.post(
            "/api/auth/register/",
            {
                "email": "registered@example.com",
                "password": "strong-pass-123",
                "display_name": "Registered User",
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(register_response.data["email"], "registered@example.com")

        login_response = self.client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": self.password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        me_response = self.client.get("/api/auth/me/")
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], self.user.email)

        logout_response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

    def test_authenticated_mvp_route_matrix(self):
        self.authenticate()

        subjects_response = self.client.get("/api/academic/subjects/")
        self.assertEqual(subjects_response.status_code, status.HTTP_200_OK)

        create_subject_response = self.client.post(
            "/api/academic/subjects/",
            {"code": "CHEM101", "name": "Chemistry", "description": "Created in smoke test"},
            format="json",
        )
        self.assertEqual(create_subject_response.status_code, status.HTTP_201_CREATED)

        subject_detail_response = self.client.get(f"/api/academic/subjects/{self.subject.id}/")
        self.assertEqual(subject_detail_response.status_code, status.HTTP_200_OK)

        resources_response = self.client.get(f"/api/academic/learning-resources/?subject={self.subject.id}")
        self.assertEqual(resources_response.status_code, status.HTTP_200_OK)

        resource_detail_response = self.client.get(f"/api/academic/learning-resources/{self.resource.id}/")
        self.assertEqual(resource_detail_response.status_code, status.HTTP_200_OK)

        sections_response = self.client.get(f"/api/academic/content-sections/?learning_resource={self.resource.id}")
        self.assertEqual(sections_response.status_code, status.HTTP_200_OK)

        concepts_response = self.client.get(f"/api/academic/content-concepts/?learning_resource={self.resource.id}")
        self.assertEqual(concepts_response.status_code, status.HTTP_200_OK)

        storage_list_response = self.client.get("/api/storage/files/")
        self.assertEqual(storage_list_response.status_code, status.HTTP_200_OK)

        storage_upload_response = self.client.post(
            "/api/storage/files/",
            {"file": SimpleUploadedFile("smoke.txt", b"smoke", content_type="text/plain")},
        )
        self.assertEqual(storage_upload_response.status_code, status.HTTP_201_CREATED)

        import_list_response = self.client.get(f"/api/content-intelligence/import-jobs/?learning_resource={self.resource.id}")
        self.assertEqual(import_list_response.status_code, status.HTTP_200_OK)

        import_create_response = self.client.post(
            "/api/content-intelligence/import-jobs/",
            {"learning_resource": str(self.resource.id)},
            format="json",
        )
        self.assertEqual(import_create_response.status_code, status.HTTP_201_CREATED)
        import_job_id = import_create_response.data["id"]

        import_retry_response = self.client.post(
            f"/api/content-intelligence/import-jobs/{import_job_id}/retry/",
            {},
            format="json",
        )
        self.assertNotServerError(
            import_retry_response,
            {status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST},
        )

        import_findings_response = self.client.get(f"/api/content-intelligence/import-jobs/{import_job_id}/findings/")
        self.assertEqual(import_findings_response.status_code, status.HTTP_200_OK)

        import_outline_response = self.client.get(f"/api/content-intelligence/import-jobs/{import_job_id}/outline/")
        self.assertIn(import_outline_response.status_code, {status.HTTP_200_OK, status.HTTP_404_NOT_FOUND})

        concept_browser_validation_response = self.client.get("/api/learning/pedagogical-sessions/concept-browser/")
        self.assertEqual(concept_browser_validation_response.status_code, status.HTTP_400_BAD_REQUEST)

        concept_browser_response = self.client.get(
            f"/api/learning/pedagogical-sessions/concept-browser/?learning_resource={self.resource.id}"
        )
        self.assertEqual(concept_browser_response.status_code, status.HTTP_200_OK)

        start_or_resume_response = self.client.post(
            "/api/learning/pedagogical-sessions/start-or-resume/",
            {"content_concept": str(self.concept.id)},
            format="json",
        )
        self.assertEqual(start_or_resume_response.status_code, status.HTTP_200_OK)
        session_id = start_or_resume_response.data["id"]

        conversation_response = self.client.get(f"/api/learning/pedagogical-sessions/{session_id}/conversation/")
        self.assertEqual(conversation_response.status_code, status.HTTP_200_OK)

        teach_response = self.client.post(f"/api/learning/pedagogical-sessions/{session_id}/teach/", {}, format="json")
        self.assertEqual(teach_response.status_code, status.HTTP_200_OK)

        ask_validation_response = self.client.post(
            f"/api/learning/pedagogical-sessions/{session_id}/ask/",
            {},
            format="json",
        )
        self.assertEqual(ask_validation_response.status_code, status.HTTP_400_BAD_REQUEST)

        ask_response = self.client.post(
            f"/api/learning/pedagogical-sessions/{session_id}/ask/",
            {"question": "What does the nucleus do?"},
            format="json",
        )
        self.assertEqual(ask_response.status_code, status.HTTP_200_OK)

        mastery_snapshot_response = self.client.get(f"/api/assessments/mastery-check/?content_concept={self.concept.id}")
        self.assertEqual(mastery_snapshot_response.status_code, status.HTTP_200_OK)

        mastery_start_response = self.client.post(
            "/api/assessments/mastery-check/start/",
            {"content_concept": str(self.concept.id)},
            format="json",
        )
        self.assertEqual(mastery_start_response.status_code, status.HTTP_400_BAD_REQUEST)

        remediation_list_response = self.client.get("/api/remediation/plans/")
        self.assertEqual(remediation_list_response.status_code, status.HTTP_200_OK)

        remediation_create_response = self.client.post(
            "/api/remediation/plans/",
            {"content_concept": str(self.concept.id), "rationale": "Review the concept again."},
            format="json",
        )
        self.assertEqual(remediation_create_response.status_code, status.HTTP_201_CREATED)
        plan_id = remediation_create_response.data["id"]

        remediation_history_response = self.client.get("/api/remediation/plans/history/")
        self.assertEqual(remediation_history_response.status_code, status.HTTP_200_OK)

        remediation_start_response = self.client.post(
            f"/api/remediation/plans/{plan_id}/start/",
            {},
            format="json",
        )
        self.assertEqual(remediation_start_response.status_code, status.HTTP_200_OK)

        remediation_complete_response = self.client.post(
            f"/api/remediation/plans/{plan_id}/complete/",
            {},
            format="json",
        )
        self.assertEqual(remediation_complete_response.status_code, status.HTTP_200_OK)
