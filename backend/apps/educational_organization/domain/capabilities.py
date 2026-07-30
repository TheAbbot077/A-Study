"""
Educational capability codes for PI-8C.1.

Capabilities represent fine-grained educational authority.
They are institution-scoped and time-bounded.
"""


class EducationalCapability:
    """Institution-level educational governance capabilities."""

    # Institution overview and management
    INSTITUTION_VIEW_OVERVIEW = "institution.view_overview"
    INSTITUTION_MANAGE_USERS = "institution.manage_users"
    INSTITUTION_MANAGE_ORGANIZATIONS = "institution.manage_organizations"

    # Academic governance
    ACADEMIC_MANAGE_PROGRAMMES = "academic.manage_programmes"
    ACADEMIC_MANAGE_COURSES = "academic.manage_courses"
    ACADEMIC_MANAGE_CLASSES = "academic.manage_classes"
    ACADEMIC_MANAGE_PERIODS = "academic.manage_periods"
    ACADEMIC_ASSIGN_TEACHERS = "academic.assign_teachers"
    ACADEMIC_ASSIGN_LEARNERS = "academic.assign_learners"
    ACADEMIC_VIEW_ANALYTICS = "academic.view_analytics"

    # Teacher capabilities
    TEACHER_VIEW_ASSIGNED_CLASSES = "teacher.view_assigned_classes"
    TEACHER_ASSIGN_WORK = "teacher.assign_work"
    TEACHER_VIEW_PROGRESS = "teacher.view_progress"
    TEACHER_CREATE_INTERVENTION = "teacher.create_intervention"

    # Learner capabilities
    LEARNER_VIEW_CLASS = "learner.view_class"
    LEARNER_VIEW_ASSIGNMENTS = "learner.view_assignments"

    @classmethod
    def get_role_bundle(cls, role_name):
        """Return capability bundle for a role."""
        bundles = {
            "institution_head": [
                cls.INSTITUTION_VIEW_OVERVIEW,
                cls.INSTITUTION_MANAGE_USERS,
                cls.INSTITUTION_MANAGE_ORGANIZATIONS,
                cls.ACADEMIC_MANAGE_PROGRAMMES,
                cls.ACADEMIC_MANAGE_COURSES,
                cls.ACADEMIC_MANAGE_CLASSES,
                cls.ACADEMIC_MANAGE_PERIODS,
                cls.ACADEMIC_ASSIGN_TEACHERS,
                cls.ACADEMIC_ASSIGN_LEARNERS,
                cls.ACADEMIC_VIEW_ANALYTICS,
            ],
            "academic_dean": [
                cls.ACADEMIC_MANAGE_PROGRAMMES,
                cls.ACADEMIC_MANAGE_COURSES,
                cls.ACADEMIC_MANAGE_CLASSES,
                cls.ACADEMIC_MANAGE_PERIODS,
                cls.ACADEMIC_ASSIGN_TEACHERS,
                cls.ACADEMIC_ASSIGN_LEARNERS,
                cls.ACADEMIC_VIEW_ANALYTICS,
            ],
            "head_of_department": [
                cls.ACADEMIC_MANAGE_PROGRAMMES,
                cls.ACADEMIC_MANAGE_COURSES,
                cls.ACADEMIC_MANAGE_CLASSES,
                cls.ACADEMIC_ASSIGN_TEACHERS,
                cls.ACADEMIC_VIEW_ANALYTICS,
            ],
            "teacher": [
                cls.TEACHER_VIEW_ASSIGNED_CLASSES,
                cls.TEACHER_ASSIGN_WORK,
                cls.TEACHER_VIEW_PROGRESS,
                cls.TEACHER_CREATE_INTERVENTION,
            ],
            "teaching_assistant": [
                cls.TEACHER_VIEW_ASSIGNED_CLASSES,
                cls.TEACHER_ASSIGN_WORK,
                cls.TEACHER_VIEW_PROGRESS,
            ],
            "tutor": [
                cls.TEACHER_VIEW_ASSIGNED_CLASSES,
                cls.TEACHER_VIEW_PROGRESS,
            ],
            "learner": [
                cls.LEARNER_VIEW_CLASS,
                cls.LEARNER_VIEW_ASSIGNMENTS,
            ],
        }
        return bundles.get(role_name, [])

    @classmethod
    def get_all_capabilities(cls):
        """Return all defined capabilities."""
        return [
            cls.INSTITUTION_VIEW_OVERVIEW,
            cls.INSTITUTION_MANAGE_USERS,
            cls.INSTITUTION_MANAGE_ORGANIZATIONS,
            cls.ACADEMIC_MANAGE_PROGRAMMES,
            cls.ACADEMIC_MANAGE_COURSES,
            cls.ACADEMIC_MANAGE_CLASSES,
            cls.ACADEMIC_MANAGE_PERIODS,
            cls.ACADEMIC_ASSIGN_TEACHERS,
            cls.ACADEMIC_ASSIGN_LEARNERS,
            cls.ACADEMIC_VIEW_ANALYTICS,
            cls.TEACHER_VIEW_ASSIGNED_CLASSES,
            cls.TEACHER_ASSIGN_WORK,
            cls.TEACHER_VIEW_PROGRESS,
            cls.TEACHER_CREATE_INTERVENTION,
            cls.LEARNER_VIEW_CLASS,
            cls.LEARNER_VIEW_ASSIGNMENTS,
        ]