from __future__ import annotations

from apps.content_intelligence.domain.models import ContentImportJob, ContentValidationFinding, ParsedConceptCandidate, ParsedSection
from apps.core.events import BusinessEvent, EventPublisher


class ValidationService:
    LARGE_SECTION_THRESHOLD = 12000

    def __init__(self, event_publisher: EventPublisher | None = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def validate(
        self,
        job: ContentImportJob,
        sections: list[ParsedSection],
        concepts: list[ParsedConceptCandidate],
        extracted_char_count: int,
    ) -> list[ContentValidationFinding]:
        findings: list[ContentValidationFinding] = []
        if not sections:
            findings.append(self._finding(job, ContentValidationFinding.Severity.CRITICAL, "missing_sections", "No sections were detected."))
        if extracted_char_count < 50:
            findings.append(self._finding(job, ContentValidationFinding.Severity.HIGH, "extraction_anomaly", "Extracted text is unusually short."))

        seen_headings: set[str] = set()
        for section in sections:
            normalized_heading = section.heading.strip().lower()
            if normalized_heading in seen_headings:
                findings.append(self._finding(job, ContentValidationFinding.Severity.MEDIUM, "duplicate_heading", f"Duplicate heading detected: {section.heading}"))
            seen_headings.add(normalized_heading)
            if len(section.body_text) > self.LARGE_SECTION_THRESHOLD:
                if (section.metadata or {}).get("section_origin") == "synthetic_fallback":
                    findings.append(
                        self._finding(
                            job,
                            ContentValidationFinding.Severity.LOW,
                            "fallback_structure_uncertain",
                            self._fallback_structure_message(section),
                        )
                    )
                else:
                    findings.append(
                        self._finding(
                            job,
                            ContentValidationFinding.Severity.LOW,
                            "abnormal_section_size",
                            f"Section is unusually large: {section.heading}",
                        )
                    )

        for concept in concepts:
            if not concept.title.strip():
                findings.append(self._finding(job, ContentValidationFinding.Severity.HIGH, "empty_concept", "A concept candidate has an empty title."))
            decision = (concept.metadata or {}).get("decision")
            if (concept.metadata or {}).get("source_label") == "synthetic_section_title":
                continue
            if decision == "manual_review":
                findings.append(
                    self._finding(
                        job,
                        ContentValidationFinding.Severity.MEDIUM,
                        "concept_manual_review",
                        f"Concept candidate requires manual review: {concept.title}",
                    )
                )
            elif decision == "rejected":
                findings.append(
                    self._finding(
                        job,
                        ContentValidationFinding.Severity.LOW,
                        "concept_rejected",
                        f"Concept candidate was rejected: {concept.title}",
                    )
                )

        self.event_publisher.publish(
            BusinessEvent.create(
                "content_intelligence.import_validated",
                payload={
                    "content_import_job_id": str(job.id),
                    "learning_resource_id": str(job.learning_resource_id),
                    "finding_count": len(findings),
                },
            )
        )
        return findings

    def _finding(self, job: ContentImportJob, severity: str, finding_type: str, message: str) -> ContentValidationFinding:
        return ContentValidationFinding(import_job=job, severity=severity, finding_type=finding_type, message=message)

    def _fallback_structure_message(self, section: ParsedSection) -> str:
        metadata = section.metadata or {}
        char_count = len(section.body_text)
        attempted = metadata.get("subdivision_attempted", False)
        found = int(metadata.get("inferred_subsections_found", 0) or 0)
        if attempted and found:
            return (
                f"Document structure could not be confidently detected. A fallback section containing "
                f"{char_count} characters was created; secondary subdivision identified {found} inferred subsections."
            )
        if attempted:
            return (
                f"Document structure could not be confidently detected. A fallback section containing "
                f"{char_count} characters was created; no reliable subdivision headings were found."
            )
        return (
            f"Document structure could not be confidently detected. A fallback section containing "
            f"{char_count} characters was created."
        )
