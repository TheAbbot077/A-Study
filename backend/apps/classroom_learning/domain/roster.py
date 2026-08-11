from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class EligibleClassroomLearner:
    learner_id: str
    institution_id: str
    class_group_id: str
    course_offering_id: str
    effective_from: object | None = None
    effective_to: object | None = None
    status: str = ""
    source_reference: str = ""


class ClassroomRosterProvider(Protocol):
    def list_eligible_learners(self, *, institution_id, class_group_id, course_offering_id, as_of=None) -> Sequence[EligibleClassroomLearner]:
        ...


class UnavailableClassroomRosterProvider:
    def list_eligible_learners(self, *, institution_id, class_group_id, course_offering_id, as_of=None):
        raise RuntimeError("ROSTER_AUTHORITY_UNAVAILABLE")
