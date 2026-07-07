from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.core.events import default_event_registry
from apps.learning.domain.models import AbbotTeachingResponse, ConversationContext, ConversationWindow
from apps.learning.services import ContextAssemblyService, GroundingService, InstructionalStrategyService
from apps.learning.services.abbot_teaching_agent_service import AbbotResponseType, AbbotTeachingAgentService


class AbbotTeachingAgentServiceTests(SimpleTestCase):
    def test_teaching_request_preparation(self):
        service, collaborators = self._service_with_mocked_collaborators()
        session = self._session()

        request = service.prepare_teaching_request(session)

        self.assertIs(request.session, session)
        self.assertEqual(request.generation_plan.response_type, "teaching")
        self.assertEqual(request.generation_plan.metadata["generator"], "deterministic_placeholder")
        self.assertEqual(request.instructional_strategy.strategy_identifier, "concept_mapping")
        collaborators["publisher"].publish.assert_called_once()
        event = collaborators["publisher"].publish.call_args.args[0]
        self.assertEqual(event.event_name, "learning.abbot_request_prepared")

    def test_context_assembly_service_is_used(self):
        service, collaborators = self._service_with_mocked_collaborators()

        service.prepare_teaching_request(self._session())

        collaborators["context"].assemble_for_session.assert_called_once()

    def test_grounding_service_is_used(self):
        service, collaborators = self._service_with_mocked_collaborators()

        service.prepare_teaching_request(self._session())

        collaborators["grounding"].build_grounding_package.assert_called_once()

    def test_instructional_strategy_service_is_used(self):
        service, collaborators = self._service_with_mocked_collaborators()

        service.prepare_teaching_request(self._session())

        collaborators["strategy"].select_strategy.assert_called_once()

    def test_conversation_orchestrator_is_used(self):
        service, collaborators = self._service_with_mocked_collaborators()

        service.prepare_teaching_request(self._session())

        collaborators["conversation"].build_conversation_context.assert_called_once()

    def test_deterministic_teaching_response_generation(self):
        service, _ = self._service_with_real_pipeline()
        session = self._session()

        first_response = service.generate_teaching_response(session)
        second_response = service.generate_teaching_response(session)

        self.assertEqual(first_response, second_response)
        self.assertEqual(first_response.response_type, AbbotResponseType.TEACHING)
        self.assertEqual([section.sequence_number for section in first_response.sections], [1, 2, 3])
        self.assertEqual(first_response.metadata["ai_provider"], None)

    def test_clarification_response_generation(self):
        service, _ = self._service_with_real_pipeline()

        response = service.generate_clarification_response(self._session(), "Why does opportunity cost matter?")

        self.assertEqual(response.response_type, AbbotResponseType.CLARIFICATION)
        self.assertIn("Why does opportunity cost matter?", response.sections[0].content)

    def test_summary_response_generation(self):
        service, _ = self._service_with_real_pipeline()

        response = service.generate_summary_response(self._session())

        self.assertEqual(response.response_type, AbbotResponseType.SUMMARY)
        self.assertEqual([section.title for section in response.sections], ["Concept Summary", "Strategy Used"])

    def test_response_validation_success(self):
        service, _ = self._service_with_real_pipeline()
        response = service.generate_teaching_response(self._session())

        validation_errors = service.validate_response(response)

        self.assertEqual(validation_errors, [])

    def test_invalid_response_validation_failure(self):
        service, _ = self._service_with_real_pipeline()
        invalid_response = AbbotTeachingResponse(
            session_id="",
            concept_title="",
            response_type="unsupported",
            sections=[],
            source_references=[],
            strategy_used=None,
        )

        validation_errors = service.validate_response(invalid_response)

        self.assertEqual(
            validation_errors,
            [
                "Abbot teaching response must use a supported response type.",
                "Abbot teaching response must include a session id.",
                "Abbot teaching response must include a concept title.",
                "Abbot teaching response must include response sections.",
                "Abbot teaching response must include source references.",
                "Abbot teaching response must include the strategy used.",
            ],
        )

    def test_response_includes_source_references(self):
        service, _ = self._service_with_real_pipeline()

        response = service.generate_teaching_response(self._session())

        self.assertTrue(response.source_references)
        self.assertIn("content_concept:concept-1", response.sections[0].source_reference_ids)

    def test_response_includes_strategy_used(self):
        service, _ = self._service_with_real_pipeline()

        response = service.generate_teaching_response(self._session())

        self.assertEqual(response.strategy_used, "concept_mapping")

    def test_abbot_message_added_to_session(self):
        service, collaborators = self._service_with_real_pipeline()
        session = self._session()

        service.generate_teaching_response(session)

        collaborators["conversation"].add_turn.assert_called_once()
        self.assertEqual(collaborators["conversation"].add_turn.call_args.kwargs["sender_type"], "abbot")
        self.assertEqual(collaborators["conversation"].add_turn.call_args.kwargs["message_type"], "explanation")

    def test_academic_content_remains_unchanged(self):
        service, _ = self._service_with_real_pipeline()
        session = self._session()
        session.content_concept.save = Mock()
        session.content_concept.content_section.save = Mock()
        session.content_concept.content_section.learning_resource.save = Mock()

        service.generate_teaching_response(session)

        self.assertEqual(session.content_concept.title, "Opportunity Cost")
        self.assertEqual(session.content_concept.content_section.title, "Economic Choices")
        self.assertEqual(session.content_concept.content_section.learning_resource.title, "Economics Guide")
        session.content_concept.save.assert_not_called()
        session.content_concept.content_section.save.assert_not_called()
        session.content_concept.content_section.learning_resource.save.assert_not_called()

    def test_events_are_published(self):
        service, collaborators = self._service_with_real_pipeline()

        response = service.generate_teaching_response(self._session())
        service.validate_response(response)

        self.assertEqual(
            [call.args[0].event_name for call in collaborators["publisher"].publish.call_args_list],
            [
                "learning.abbot_request_prepared",
                "learning.abbot_response_generated",
                "learning.abbot_response_validated",
            ],
        )

    def test_abbot_events_are_registered_for_discovery(self):
        registered_event_names = set(default_event_registry._subscribers)

        self.assertIn("learning.abbot_request_prepared", registered_event_names)
        self.assertIn("learning.abbot_response_generated", registered_event_names)
        self.assertIn("learning.abbot_response_validated", registered_event_names)

    def _service_with_mocked_collaborators(self):
        context = self._context()
        package = GroundingService(event_publisher=Mock()).build_grounding_package(context)
        strategy = InstructionalStrategyService(event_publisher=Mock()).select_strategy(package).strategy
        conversation_context = self._conversation_context(package, strategy)

        context_service = Mock()
        context_service.assemble_for_session.return_value = context
        grounding_service = Mock()
        grounding_service.build_grounding_package.return_value = package
        strategy_service = Mock()
        strategy_service.select_strategy.return_value = SimpleNamespace(strategy=strategy)
        conversation = Mock()
        conversation.build_conversation_context.return_value = conversation_context
        publisher = Mock()

        service = AbbotTeachingAgentService(
            event_publisher=publisher,
            context_assembly_service=context_service,
            grounding_service=grounding_service,
            strategy_service=strategy_service,
            conversation_orchestrator=conversation,
        )
        return service, {
            "context": context_service,
            "grounding": grounding_service,
            "strategy": strategy_service,
            "conversation": conversation,
            "publisher": publisher,
        }

    def _service_with_real_pipeline(self):
        conversation = Mock()
        publisher = Mock()
        conversation.build_conversation_context.side_effect = lambda session: self._conversation_context_for_session(session)
        service = AbbotTeachingAgentService(
            event_publisher=publisher,
            context_assembly_service=ContextAssemblyService(event_publisher=Mock()),
            grounding_service=GroundingService(event_publisher=Mock()),
            strategy_service=InstructionalStrategyService(event_publisher=Mock()),
            conversation_orchestrator=conversation,
        )
        return service, {"conversation": conversation, "publisher": publisher}

    def _conversation_context_for_session(self, session):
        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_session(session)
        package = GroundingService(event_publisher=Mock()).build_grounding_package(context)
        strategy = InstructionalStrategyService(event_publisher=Mock()).select_strategy(package).strategy
        return self._conversation_context(package, strategy)

    def _conversation_context(self, package, strategy):
        return ConversationContext(
            pedagogical_session=SimpleNamespace(id="session-1"),
            grounded_teaching_package=package,
            instructional_strategy=strategy,
            active_conversation_window=ConversationWindow(turns=[], window_size=12),
            current_turn_number=0,
            current_instructional_step=strategy.ordered_instructional_steps[0],
        )

    def _context(self):
        return ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(
            SimpleNamespace(id="learner-1"),
            self._academic_concept(),
            session_id="session-1",
        )

    def _session(self):
        return SimpleNamespace(id="session-1", learner=SimpleNamespace(id="learner-1"), content_concept=self._academic_concept())

    def _academic_concept(self):
        subject = SimpleNamespace(id="subject-1", name="Economics")
        curriculum = SimpleNamespace(id="curriculum-1", name="Intro Economics")
        curriculum_unit = SimpleNamespace(id="unit-1", title="Scarcity", sequence_number=1)
        resource = SimpleNamespace(
            id="resource-1",
            title="Economics Guide",
            resource_type="guide",
            subject=subject,
            curriculum=curriculum,
            curriculum_unit=curriculum_unit,
        )
        section = SimpleNamespace(
            id="section-1",
            title="Economic Choices",
            sequence_number=1,
            review_status="approved",
            quality_status="high",
            learning_resource=resource,
        )
        return SimpleNamespace(
            id="concept-1",
            title="Opportunity Cost",
            description="The value of the next best alternative.",
            learning_objective="Explain opportunity cost.",
            sequence_number=2,
            review_status="approved",
            quality_status="high",
            content_section=section,
        )
