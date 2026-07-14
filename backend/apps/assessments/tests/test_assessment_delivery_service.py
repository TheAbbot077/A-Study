import uuid

from unittest.mock import Mock, patch

from django.db import models
from django.test import SimpleTestCase

from apps.assessments.domain.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentDeliveryItem,
    AssessmentDeliverySession,
    AssessmentDeliveryState,
    AssessmentItem,
    AssessmentItemBankLink,
    AssessmentItemType,
    AssessmentResponse,
    AssessmentState,
)
from apps.assessments.services import AssessmentDeliveryService
from apps.assessments.services import assessment_delivery_service as delivery_module
from apps.core.events import default_event_registry


class DummyLearner:
    id = "learner-1"


class AssessmentDeliveryServiceTests(SimpleTestCase):
    def test_create_delivery_session(self):
        publisher = Mock()
        service = AssessmentDeliveryService(event_publisher=publisher)
        assessment = self._assessment()
        learner = DummyLearner()

        with patch("apps.assessments.services.assessment_delivery_service.AssessmentAttempt.objects") as attempt_objects:
            with patch("apps.assessments.services.assessment_delivery_service.AssessmentDeliverySession.objects") as session_objects:
                attempt = self._attempt(assessment, learner)
                session = self._session(assessment, learner, attempt)
                attempt_objects.create.return_value = attempt
                session_objects.create.return_value = session

                delivery_session = service.create_delivery_session(assessment, learner)

        self.assertIs(delivery_session, session)
        attempt_objects.create.assert_called_once()
        session_objects.create.assert_called_once()
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.delivery_session_created")

    def test_start_delivery_session(self):
        session = self._session()

        AssessmentDeliveryService(event_publisher=Mock()).start_delivery_session(session)

        self.assertEqual(session.status, AssessmentDeliveryState.ACTIVE)
        self.assertIsNotNone(session.started_at)
        self.assertEqual(session.assessment_attempt.state, AssessmentState.ACTIVE)
        session.assessment_attempt.save.assert_called_once()
        session.save.assert_called_once()

    def test_delivery_session_links_or_creates_attempt(self):
        service = AssessmentDeliveryService(event_publisher=Mock())

        with patch("apps.assessments.services.assessment_delivery_service.AssessmentAttempt.objects") as attempt_objects:
            with patch("apps.assessments.services.assessment_delivery_service.AssessmentDeliverySession.objects") as session_objects:
                attempt = self._attempt()
                session = self._session(attempt=attempt)
                attempt_objects.create.return_value = attempt
                session_objects.create.return_value = session

                created = service.create_delivery_session(session.assessment, session.learner)

        self.assertIs(created.assessment_attempt, attempt)

    def test_items_listed_in_sequence_order(self):
        service = AssessmentDeliveryService(event_publisher=Mock())
        session = self._session()
        expected_links = [self._bank_link(1), self._bank_link(2)]

        with patch("apps.assessments.services.assessment_delivery_service.AssessmentItemBankLink.objects") as link_objects:
            link_objects.filter.return_value.order_by.return_value = expected_links
            delivery_items = service.list_delivery_items(session)

        self.assertEqual([item.sequence_number for item in delivery_items], [1, 2])
        link_objects.filter.return_value.order_by.assert_called_once_with("sequence_number")

    def test_get_current_item(self):
        publisher = Mock()
        service = AssessmentDeliveryService(event_publisher=publisher)
        session = self._session()
        session.current_sequence_number = 2

        with patch.object(service, "list_delivery_items", return_value=[self._delivery_item(1), self._delivery_item(2)]):
            current_item = service.get_current_item(session)

        self.assertEqual(current_item.sequence_number, 2)
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.delivery_item_presented")

    def test_move_to_next_item(self):
        service = AssessmentDeliveryService(event_publisher=Mock())
        session = self._session()
        session.current_sequence_number = 1

        with patch.object(service, "list_delivery_items", return_value=[self._delivery_item(1), self._delivery_item(2)]):
            with patch.object(service, "get_current_item", return_value=self._delivery_item(2)) as get_current:
                next_item = service.move_to_next_item(session)

        self.assertEqual(session.current_sequence_number, 2)
        session.save.assert_called_once()
        self.assertEqual(next_item.sequence_number, 2)
        get_current.assert_called_once_with(session)

    def test_cannot_move_beyond_final_item_without_predictable_behavior(self):
        service = AssessmentDeliveryService(event_publisher=Mock())
        session = self._session()
        session.current_sequence_number = 2

        with patch.object(service, "list_delivery_items", return_value=[self._delivery_item(1), self._delivery_item(2)]):
            with patch.object(service, "get_current_item", return_value=self._delivery_item(2)):
                next_item = service.move_to_next_item(session)

        self.assertEqual(session.current_sequence_number, 2)
        self.assertEqual(next_item.sequence_number, 2)
        session.save.assert_not_called()

    def test_submit_response_records_assessment_response(self):
        publisher = Mock()
        service = AssessmentDeliveryService(event_publisher=publisher)
        session = self._session()
        item = self._assessment_item()

        with patch("apps.assessments.services.assessment_delivery_service.AssessmentResponse.objects") as response_objects:
            response = Mock(spec=AssessmentResponse)
            response.id = "response-1"
            response_objects.create.return_value = response

            submitted = service.submit_response(session, item, {"answer": "A"})

        self.assertIs(submitted, response)
        response_objects.create.assert_called_once_with(
            attempt=session.assessment_attempt,
            item=item,
            response_data={"answer": "A"},
            metadata={},
        )
        self.assertEqual(session.assessment_attempt.state, AssessmentState.SUBMITTED)
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.delivery_response_submitted")

    def test_submit_response_rejects_inactive_delivery_session(self):
        session = self._session()
        session.status = AssessmentDeliveryState.COMPLETED

        with self.assertRaises(ValueError):
            AssessmentDeliveryService(event_publisher=Mock()).submit_response(session, self._assessment_item(), {"answer": "A"})

    def test_submit_response_requires_attempt(self):
        session = self._session()
        session.status = AssessmentDeliveryState.ACTIVE
        session.assessment_attempt = None
        session.assessment_attempt_id = None

        with self.assertRaises(ValueError):
            AssessmentDeliveryService(event_publisher=Mock()).submit_response(session, self._assessment_item(), {"answer": "A"})

    def test_submit_delivery_session(self):
        session = self._session()

        AssessmentDeliveryService(event_publisher=Mock()).submit_delivery_session(session)

        self.assertEqual(session.status, AssessmentDeliveryState.SUBMITTED)
        self.assertEqual(session.assessment_attempt.state, AssessmentState.SUBMITTED)
        session.save.assert_called_once()

    def test_complete_delivery_session(self):
        session = self._session()

        AssessmentDeliveryService(event_publisher=Mock()).complete_delivery_session(session)

        self.assertEqual(session.status, AssessmentDeliveryState.COMPLETED)
        self.assertEqual(session.assessment_attempt.state, AssessmentState.COMPLETED)
        session.save.assert_called_once()

    def test_abandon_delivery_session(self):
        session = self._session()

        AssessmentDeliveryService(event_publisher=Mock()).abandon_delivery_session(session)

        self.assertEqual(session.status, AssessmentDeliveryState.ABANDONED)
        self.assertIsNotNone(session.completed_at)
        session.save.assert_called_once()

    def test_delivery_does_not_grade_responses(self):
        session = self._session()
        item = self._assessment_item()

        with patch("apps.assessments.services.assessment_delivery_service.AssessmentResponse.objects") as response_objects:
            response_objects.create.return_value = Mock(spec=AssessmentResponse, id="response-1")
            if hasattr(delivery_module, "AssessmentEvaluation"):
                with patch.object(delivery_module.AssessmentEvaluation, "objects") as evaluation_objects:
                    AssessmentDeliveryService(event_publisher=Mock()).submit_response(session, item, {"answer": "A"})
                    evaluation_objects.create.assert_not_called()
            else:
                AssessmentDeliveryService(event_publisher=Mock()).submit_response(session, item, {"answer": "A"})

        response_objects.create.assert_called_once()

    def test_delivery_does_not_update_mastery(self):
        session = self._session()
        session.mastery_profile = Mock()

        AssessmentDeliveryService(event_publisher=Mock()).complete_delivery_session(session)

        session.mastery_profile.save.assert_not_called()

    def test_item_order_preserved_for_assessment_items(self):
        service = AssessmentDeliveryService(event_publisher=Mock())
        session = self._session()
        expected_items = [self._assessment_item(1), self._assessment_item(2)]

        with patch("apps.assessments.services.assessment_delivery_service.AssessmentItemBankLink.objects") as link_objects:
            with patch("apps.assessments.services.assessment_delivery_service.AssessmentItem.objects") as item_objects:
                link_objects.filter.return_value.order_by.return_value = []
                item_objects.filter.return_value.order_by.return_value = expected_items
                delivery_items = service.list_delivery_items(session)

        self.assertEqual([item.sequence_number for item in delivery_items], [1, 2])
        item_objects.filter.return_value.order_by.assert_called_once_with("sequence_number")

    def test_list_delivery_sessions_for_learner(self):
        service = AssessmentDeliveryService(event_publisher=Mock())
        learner = DummyLearner()
        expected = [self._session()]

        with patch("apps.assessments.services.assessment_delivery_service.AssessmentDeliverySession.objects") as session_objects:
            session_objects.filter.return_value.order_by.return_value = expected
            sessions = service.list_delivery_sessions_for_learner(learner)

        self.assertEqual(sessions, expected)
        session_objects.filter.assert_called_once_with(learner=learner)
        session_objects.filter.return_value.order_by.assert_called_once_with("-created_at")

    def test_event_publishing_for_delivery_lifecycle_actions(self):
        publisher = Mock()
        service = AssessmentDeliveryService(event_publisher=publisher)
        session = self._session()

        service.start_delivery_session(session)
        with patch.object(service, "list_delivery_items", return_value=[self._delivery_item(1)]):
            service.get_current_item(session)
        service.submit_delivery_session(session)
        service.complete_delivery_session(session)
        service.abandon_delivery_session(session)

        event_names = [call.args[0].event_name for call in publisher.publish.call_args_list]

        self.assertEqual(
            event_names,
            [
                "assessment.delivery_session_started",
                "assessment.delivery_item_presented",
                "assessment.delivery_session_submitted",
                "assessment.delivery_session_completed",
            ],
        )

    def test_abandon_completed_session_is_no_op(self):
        publisher = Mock()
        service = AssessmentDeliveryService(event_publisher=publisher)
        session = self._session()

        service.complete_delivery_session(session)
        save_call_count = session.save.call_count
        completed_at = session.completed_at

        returned = service.abandon_delivery_session(session)

        self.assertIs(returned, session)
        self.assertEqual(session.status, AssessmentDeliveryState.COMPLETED)
        self.assertEqual(session.completed_at, completed_at)
        self.assertEqual(session.save.call_count, save_call_count)
        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            ["assessment.delivery_session_completed"],
        )

    def test_delivery_events_are_registered_for_discovery(self):
        expected = {
            "assessment.delivery_session_created",
            "assessment.delivery_session_started",
            "assessment.delivery_item_presented",
            "assessment.delivery_response_submitted",
            "assessment.delivery_session_submitted",
            "assessment.delivery_session_completed",
            "assessment.delivery_session_abandoned",
        }

        self.assertTrue(expected.issubset(set(default_event_registry._subscribers)))

    def test_delivery_session_model_constraints(self):
        constraints = {constraint.name: constraint for constraint in AssessmentDeliverySession._meta.constraints}

        self.assertIn("assessment_delivery_current_sequence_gte_1", constraints)
        self.assertIsInstance(constraints["assessment_delivery_current_sequence_gte_1"], models.CheckConstraint)

    def _assessment(self):
        assessment = Mock(spec=Assessment)
        assessment.id = "assessment-1"
        return assessment

    def _attempt(self, assessment=None, learner=None):
        attempt = Mock(spec=AssessmentAttempt)
        attempt.id = "attempt-1"
        attempt.assessment = assessment or self._assessment()
        attempt.learner = learner or DummyLearner()
        attempt.state = AssessmentState.CREATED
        attempt.started_at = None
        attempt.submitted_at = None
        attempt.completed_at = None
        attempt.save = Mock()
        return attempt

    def _session(self, assessment=None, learner=None, attempt=None):
        assessment = assessment or self._assessment()
        learner = learner or DummyLearner()
        attempt = attempt or self._attempt(assessment, learner)
        session = Mock(spec=AssessmentDeliverySession)
        session.id = "delivery-session-1"
        session.assessment = assessment
        session.assessment_id = assessment.id
        session.learner = learner
        session.learner_id = learner.id
        session.assessment_attempt = attempt
        session.assessment_attempt_id = attempt.id
        session.status = AssessmentDeliveryState.CREATED
        session.current_sequence_number = 1
        session.started_at = None
        session.submitted_at = None
        session.completed_at = None
        session.save = Mock()
        return session

    def _assessment_item(self, sequence_number=1):
        return AssessmentItem(
            id=uuid.uuid4(),
            item_type=AssessmentItemType.SHORT_ANSWER,
            prompt="Explain the concept.",
            sequence_number=sequence_number,
        )

    def _bank_link(self, sequence_number):
        link = Mock(spec=AssessmentItemBankLink)
        link.id = f"bank-link-{sequence_number}"
        link.sequence_number = sequence_number
        link.item_bank_entry_id = f"bank-entry-{sequence_number}"
        return link

    def _delivery_item(self, sequence_number):
        return AssessmentDeliveryItem(
            sequence_number=sequence_number,
            item=self._assessment_item(sequence_number),
            source_type="assessment_item",
        )
