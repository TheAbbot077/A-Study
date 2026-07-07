from django.test import SimpleTestCase

from apps.core.events import default_event_registry


class AcademicArchitectureTests(SimpleTestCase):
    def test_all_academic_events_are_registered_for_discovery(self):
        expected_event_names = {
            "academic.subject_created",
            "academic.subject_updated",
            "academic.subject_archived",
            "academic.curriculum_created",
            "academic.curriculum_updated",
            "academic.curriculum_archived",
            "academic.curriculum_unit_created",
            "academic.curriculum_unit_updated",
            "academic.curriculum_unit_archived",
            "academic.learning_resource_created",
            "academic.learning_resource_updated",
            "academic.learning_resource_activated",
            "academic.learning_resource_archived",
            "academic.content_section_created",
            "academic.content_section_updated",
            "academic.content_section_archived",
            "academic.content_concept_created",
            "academic.content_concept_updated",
            "academic.content_concept_archived",
            "academic.content_section_submitted_for_review",
            "academic.content_section_approved",
            "academic.content_section_rejected",
            "academic.content_section_quality_marked",
            "academic.content_concept_submitted_for_review",
            "academic.content_concept_approved",
            "academic.content_concept_rejected",
            "academic.content_concept_quality_marked",
            "academic.manual_section_created",
            "academic.manual_section_updated",
            "academic.manual_section_archived",
            "academic.manual_section_reordered",
            "academic.manual_concept_created",
            "academic.manual_concept_updated",
            "academic.manual_concept_archived",
            "academic.manual_concept_reordered",
            "academic.resource_ingestion_job_created",
            "academic.resource_ingestion_job_started",
            "academic.resource_ingestion_job_completed",
            "academic.resource_ingestion_job_failed",
            "academic.resource_ingestion_job_cancelled",
        }

        registered_event_names = set(default_event_registry._subscribers)

        self.assertTrue(expected_event_names.issubset(registered_event_names))
