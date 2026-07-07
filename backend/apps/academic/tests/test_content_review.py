from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.academic.domain.models import ContentConcept, ContentSection
from apps.academic.services.content_review_service import ContentReviewService


class ContentReviewServiceTests(SimpleTestCase):
    def test_default_section_review_status_is_draft(self):
        field = ContentSection._meta.get_field("review_status")

        self.assertEqual(field.default, ContentSection.ReviewStatus.DRAFT)

    def test_default_section_quality_status_is_unknown(self):
        field = ContentSection._meta.get_field("quality_status")

        self.assertEqual(field.default, ContentSection.QualityStatus.UNKNOWN)

    def test_submit_section_for_review(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        section = self._section()

        submitted_section = service.submit_section_for_review(section, submitted_by=self._user(), notes="Ready")

        self.assertIs(submitted_section, section)
        self.assertEqual(section.review_status, ContentSection.ReviewStatus.IN_REVIEW)
        self.assertEqual(section.review_notes, "Ready")
        section.save.assert_called_once()
        self._assert_last_event(publisher, "academic.content_section_submitted_for_review")

    def test_approve_section_sets_approved_at_and_approved_by(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        section = self._section()
        user = self._user()

        with patch("apps.academic.services.content_review_service.timezone") as timezone:
            timezone.now.return_value = "now"
            approved_section = service.approve_section(section, approved_by=user, notes="Approved")

        self.assertIs(approved_section, section)
        self.assertEqual(section.review_status, ContentSection.ReviewStatus.APPROVED)
        self.assertEqual(section.approved_at, "now")
        self.assertIs(section.approved_by, user)
        self.assertEqual(section.review_notes, "Approved")
        self._assert_last_event(publisher, "academic.content_section_approved")

    def test_reject_section_does_not_set_approved_at(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        section = self._section()
        section.approved_at = "previous"
        section.approved_by = self._user("previous-user")

        rejected_section = service.reject_section(section, rejected_by=self._user(), notes="Needs work")

        self.assertIs(rejected_section, section)
        self.assertEqual(section.review_status, ContentSection.ReviewStatus.REJECTED)
        self.assertIsNone(section.approved_at)
        self.assertIsNone(section.approved_by)
        self.assertEqual(section.review_notes, "Needs work")
        self._assert_last_event(publisher, "academic.content_section_rejected")

    def test_mark_section_quality(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        section = self._section()

        marked_section = service.mark_section_quality(
            section,
            ContentSection.QualityStatus.HIGH,
            marked_by=self._user(),
            notes="Strong coverage",
        )

        self.assertIs(marked_section, section)
        self.assertEqual(section.quality_status, ContentSection.QualityStatus.HIGH)
        self.assertEqual(section.review_notes, "Strong coverage")
        self._assert_last_event(publisher, "academic.content_section_quality_marked")

    def test_default_concept_review_status_is_draft(self):
        field = ContentConcept._meta.get_field("review_status")

        self.assertEqual(field.default, ContentConcept.ReviewStatus.DRAFT)

    def test_default_concept_quality_status_is_unknown(self):
        field = ContentConcept._meta.get_field("quality_status")

        self.assertEqual(field.default, ContentConcept.QualityStatus.UNKNOWN)

    def test_submit_concept_for_review(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        concept = self._concept()

        submitted_concept = service.submit_concept_for_review(concept, submitted_by=self._user(), notes="Ready")

        self.assertIs(submitted_concept, concept)
        self.assertEqual(concept.review_status, ContentConcept.ReviewStatus.IN_REVIEW)
        self.assertEqual(concept.review_notes, "Ready")
        concept.save.assert_called_once()
        self._assert_last_event(publisher, "academic.content_concept_submitted_for_review")

    def test_approve_concept_sets_approved_at_and_approved_by(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        concept = self._concept()
        user = self._user()

        with patch("apps.academic.services.content_review_service.timezone") as timezone:
            timezone.now.return_value = "now"
            approved_concept = service.approve_concept(concept, approved_by=user, notes="Approved")

        self.assertIs(approved_concept, concept)
        self.assertEqual(concept.review_status, ContentConcept.ReviewStatus.APPROVED)
        self.assertEqual(concept.approved_at, "now")
        self.assertIs(concept.approved_by, user)
        self.assertEqual(concept.review_notes, "Approved")
        self._assert_last_event(publisher, "academic.content_concept_approved")

    def test_reject_concept_does_not_set_approved_at(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        concept = self._concept()
        concept.approved_at = "previous"
        concept.approved_by = self._user("previous-user")

        rejected_concept = service.reject_concept(concept, rejected_by=self._user(), notes="Needs work")

        self.assertIs(rejected_concept, concept)
        self.assertEqual(concept.review_status, ContentConcept.ReviewStatus.REJECTED)
        self.assertIsNone(concept.approved_at)
        self.assertIsNone(concept.approved_by)
        self.assertEqual(concept.review_notes, "Needs work")
        self._assert_last_event(publisher, "academic.content_concept_rejected")

    def test_mark_concept_quality(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        concept = self._concept()

        marked_concept = service.mark_concept_quality(
            concept,
            ContentConcept.QualityStatus.NEEDS_ATTENTION,
            marked_by=self._user(),
            notes="Needs examples",
        )

        self.assertIs(marked_concept, concept)
        self.assertEqual(concept.quality_status, ContentConcept.QualityStatus.NEEDS_ATTENTION)
        self.assertEqual(concept.review_notes, "Needs examples")
        self._assert_last_event(publisher, "academic.content_concept_quality_marked")

    def test_event_publishing_for_all_section_review_actions(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        section = self._section()
        user = self._user()

        with patch("apps.academic.services.content_review_service.timezone") as timezone:
            timezone.now.return_value = "now"
            service.submit_section_for_review(section, submitted_by=user)
            service.approve_section(section, approved_by=user)
            service.reject_section(section, rejected_by=user)
            service.mark_section_quality(section, ContentSection.QualityStatus.ACCEPTABLE, marked_by=user)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            [
                "academic.content_section_submitted_for_review",
                "academic.content_section_approved",
                "academic.content_section_rejected",
                "academic.content_section_quality_marked",
            ],
        )

    def test_event_publishing_for_all_concept_review_actions(self):
        publisher = Mock()
        service = ContentReviewService(event_publisher=publisher)
        concept = self._concept()
        user = self._user()

        with patch("apps.academic.services.content_review_service.timezone") as timezone:
            timezone.now.return_value = "now"
            service.submit_concept_for_review(concept, submitted_by=user)
            service.approve_concept(concept, approved_by=user)
            service.reject_concept(concept, rejected_by=user)
            service.mark_concept_quality(concept, ContentConcept.QualityStatus.ACCEPTABLE, marked_by=user)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            [
                "academic.content_concept_submitted_for_review",
                "academic.content_concept_approved",
                "academic.content_concept_rejected",
                "academic.content_concept_quality_marked",
            ],
        )

    def test_invalid_section_quality_status_rejected(self):
        service = ContentReviewService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.mark_section_quality(self._section(), "excellent")

    def test_invalid_concept_quality_status_rejected(self):
        service = ContentReviewService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.mark_concept_quality(self._concept(), "excellent")

    def test_invalid_section_review_status_rejected_by_model_choices(self):
        field = ContentSection._meta.get_field("review_status")

        with self.assertRaises(ValidationError):
            field.clean("pending_review", None)

    def test_invalid_concept_review_status_rejected_by_model_choices(self):
        field = ContentConcept._meta.get_field("review_status")

        with self.assertRaises(ValidationError):
            field.clean("pending_review", None)

    def _section(self):
        section = Mock(spec=ContentSection)
        section.id = "section-1"
        section.learning_resource_id = "resource-1"
        section.review_status = ContentSection.ReviewStatus.DRAFT
        section.quality_status = ContentSection.QualityStatus.UNKNOWN
        section.review_notes = ""
        section.approved_at = None
        section.approved_by = None
        return section

    def _concept(self):
        concept = Mock(spec=ContentConcept)
        concept.id = "concept-1"
        concept.content_section_id = "section-1"
        concept.review_status = ContentConcept.ReviewStatus.DRAFT
        concept.quality_status = ContentConcept.QualityStatus.UNKNOWN
        concept.review_notes = ""
        concept.approved_at = None
        concept.approved_by = None
        return concept

    def _user(self, user_id="user-1"):
        user = Mock()
        user.id = user_id
        return user

    def _assert_last_event(self, publisher, event_name):
        publisher.publish.assert_called()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, event_name)
