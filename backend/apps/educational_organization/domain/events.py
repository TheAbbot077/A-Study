"""
Educational organization domain events.

Events describe business facts and remain idempotent.
Payloads contain identifiers only.
"""


class EducationalOrganizationCreated:
    event_type = "educational_organization.created"
    version = 1

    def __init__(self, organization_id, institution_id, name, organization_type, parent_id=None):
        self.organization_id = organization_id
        self.institution_id = institution_id
        self.name = name
        self.organization_type = organization_type
        self.parent_id = parent_id

    def payload(self):
        return {
            "organization_id": str(self.organization_id),
            "institution_id": str(self.institution_id),
            "name": self.name,
            "organization_type": self.organization_type,
            "parent_id": str(self.parent_id) if self.parent_id else None,
        }


class AcademicUnitCreated:
    event_type = "academic_unit.created"
    version = 1

    def __init__(self, unit_id, institution_id, organization_id, name, unit_type, parent_id=None):
        self.unit_id = unit_id
        self.institution_id = institution_id
        self.organization_id = organization_id
        self.name = name
        self.unit_type = unit_type
        self.parent_id = parent_id

    def payload(self):
        return {
            "unit_id": str(self.unit_id),
            "institution_id": str(self.institution_id),
            "organization_id": str(self.organization_id),
            "name": self.name,
            "unit_type": self.unit_type,
            "parent_id": str(self.parent_id) if self.parent_id else None,
        }


class ProgrammeActivated:
    event_type = "programme.activated"
    version = 1

    def __init__(self, programme_id, institution_id, organization_id, unit_id, name):
        self.programme_id = programme_id
        self.institution_id = institution_id
        self.organization_id = organization_id
        self.unit_id = unit_id
        self.name = name

    def payload(self):
        return {
            "programme_id": str(self.programme_id),
            "institution_id": str(self.institution_id),
            "organization_id": str(self.organization_id),
            "unit_id": str(self.unit_id),
            "name": self.name,
        }


class AcademicPeriodOpened:
    event_type = "academic_period.opened"
    version = 1

    def __init__(self, period_id, institution_id, organization_id, name, period_type, starts_at, ends_at):
        self.period_id = period_id
        self.institution_id = institution_id
        self.organization_id = organization_id
        self.name = name
        self.period_type = period_type
        self.starts_at = starts_at
        self.ends_at = ends_at

    def payload(self):
        return {
            "period_id": str(self.period_id),
            "institution_id": str(self.institution_id),
            "organization_id": str(self.organization_id),
            "name": self.name,
            "period_type": self.period_type,
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
        }


class CourseOfferingCreated:
    event_type = "course_offering.created"
    version = 1

    def __init__(self, offering_id, institution_id, organization_id, unit_id, programme_id, period_id, subject_id, name):
        self.offering_id = offering_id
        self.institution_id = institution_id
        self.organization_id = organization_id
        self.unit_id = unit_id
        self.programme_id = programme_id
        self.period_id = period_id
        self.subject_id = subject_id
        self.name = name

    def payload(self):
        return {
            "offering_id": str(self.offering_id),
            "institution_id": str(self.institution_id),
            "organization_id": str(self.organization_id),
            "unit_id": str(self.unit_id),
            "programme_id": str(self.programme_id),
            "period_id": str(self.period_id),
            "subject_id": str(self.subject_id),
            "name": self.name,
        }


class ClassGroupCreated:
    event_type = "class_group.created"
    version = 1

    def __init__(self, class_group_id, institution_id, organization_id, unit_id, offering_id, name):
        self.class_group_id = class_group_id
        self.institution_id = institution_id
        self.organization_id = organization_id
        self.unit_id = unit_id
        self.offering_id = offering_id
        self.name = name

    def payload(self):
        return {
            "class_group_id": str(self.class_group_id),
            "institution_id": str(self.institution_id),
            "organization_id": str(self.organization_id),
            "unit_id": str(self.unit_id),
            "offering_id": str(self.offering_id),
            "name": self.name,
        }


class TeacherAssigned:
    event_type = "teacher.assigned"
    version = 1

    def __init__(self, assignment_id, institution_id, teacher_id, class_group_id, course_offering_id, subject_id, effective_from):
        self.assignment_id = assignment_id
        self.institution_id = institution_id
        self.teacher_id = teacher_id
        self.class_group_id = class_group_id
        self.course_offering_id = course_offering_id
        self.subject_id = subject_id
        self.effective_from = effective_from

    def payload(self):
        return {
            "assignment_id": str(self.assignment_id),
            "institution_id": str(self.institution_id),
            "teacher_id": str(self.teacher_id),
            "class_group_id": str(self.class_group_id),
            "course_offering_id": str(self.course_offering_id),
            "subject_id": str(self.subject_id),
            "effective_from": self.effective_from.isoformat(),
        }


class TeacherUnassigned:
    event_type = "teacher.unassigned"
    version = 1

    def __init__(self, assignment_id, institution_id, teacher_id, class_group_id, course_offering_id, subject_id):
        self.assignment_id = assignment_id
        self.institution_id = institution_id
        self.teacher_id = teacher_id
        self.class_group_id = class_group_id
        self.course_offering_id = course_offering_id
        self.subject_id = subject_id

    def payload(self):
        return {
            "assignment_id": str(self.assignment_id),
            "institution_id": str(self.institution_id),
            "teacher_id": str(self.teacher_id),
            "class_group_id": str(self.class_group_id),
            "course_offering_id": str(self.course_offering_id),
            "subject_id": str(self.subject_id),
        }


class LearnerEnrolled:
    event_type = "learner.enrolled"
    version = 1

    def __init__(self, class_group_id, institution_id, learner_id):
        self.class_group_id = class_group_id
        self.institution_id = institution_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "class_group_id": str(self.class_group_id),
            "institution_id": str(self.institution_id),
            "learner_id": str(self.learner_id),
        }


class LearnerWithdrawn:
    event_type = "learner.withdrawn"
    version = 1

    def __init__(self, class_group_id, institution_id, learner_id):
        self.class_group_id = class_group_id
        self.institution_id = institution_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "class_group_id": str(self.class_group_id),
            "institution_id": str(self.institution_id),
            "learner_id": str(self.learner_id),
        }


class TeachingAssignmentActivated:
    event_type = "teaching_assignment.activated"
    version = 1

    def __init__(self, assignment_id, institution_id, teacher_id, class_group_id):
        self.assignment_id = assignment_id
        self.institution_id = institution_id
        self.teacher_id = teacher_id
        self.class_group_id = class_group_id

    def payload(self):
        return {
            "assignment_id": str(self.assignment_id),
            "institution_id": str(self.institution_id),
            "teacher_id": str(self.teacher_id),
            "class_group_id": str(self.class_group_id),
        }


class TeachingAssignmentExpired:
    event_type = "teaching_assignment.expired"
    version = 1

    def __init__(self, assignment_id, institution_id, teacher_id, class_group_id):
        self.assignment_id = assignment_id
        self.institution_id = institution_id
        self.teacher_id = teacher_id
        self.class_group_id = class_group_id

    def payload(self):
        return {
            "assignment_id": str(self.assignment_id),
            "institution_id": str(self.institution_id),
            "teacher_id": str(self.teacher_id),
            "class_group_id": str(self.class_group_id),
        }