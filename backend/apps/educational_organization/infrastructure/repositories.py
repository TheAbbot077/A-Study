from django.db.models import Q
from django.utils import timezone

from apps.educational_organization.domain.models import (
    AcademicPeriod,
    AcademicUnit,
    ClassGroup,
    CourseOffering,
    EducationalOrganization,
    Programme,
    TeachingAssignment,
    TeachingAssignmentStatus,
)


class EducationalOrganizationRepository:
    @staticmethod
    def get_by_id(organization_id):
        return EducationalOrganization.objects.select_related("institution", "parent").filter(pk=organization_id).first()

    @staticmethod
    def list_by_institution(institution_id, status=None):
        queryset = EducationalOrganization.objects.filter(institution_id=institution_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related("institution", "parent").order_by("name")

    @staticmethod
    def get_hierarchy(institution_id, root_id=None):
        queryset = EducationalOrganization.objects.filter(institution_id=institution_id)
        if root_id:
            queryset = queryset.filter(Q(pk=root_id) | Q(parent_id=root_id))
        return queryset.select_related("institution", "parent").order_by("name")


class AcademicUnitRepository:
    @staticmethod
    def get_by_id(unit_id):
        return AcademicUnit.objects.select_related("institution", "educational_organization", "parent").filter(pk=unit_id).first()

    @staticmethod
    def list_by_organization(organization_id, status=None):
        queryset = AcademicUnit.objects.filter(educational_organization_id=organization_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related("institution", "educational_organization", "parent").order_by("name")

    @staticmethod
    def list_by_institution(institution_id, status=None):
        queryset = AcademicUnit.objects.filter(institution_id=institution_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related("institution", "educational_organization", "parent").order_by("name")


class ProgrammeRepository:
    @staticmethod
    def get_by_id(programme_id):
        return Programme.objects.select_related("institution", "educational_organization", "academic_unit").filter(pk=programme_id).first()

    @staticmethod
    def list_by_unit(unit_id, status=None):
        queryset = Programme.objects.filter(academic_unit_id=unit_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related("institution", "educational_organization", "academic_unit").order_by("name")

    @staticmethod
    def list_by_institution(institution_id, status=None):
        queryset = Programme.objects.filter(institution_id=institution_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related("institution", "educational_organization", "academic_unit").order_by("name")


class AcademicPeriodRepository:
    @staticmethod
    def get_by_id(period_id):
        return AcademicPeriod.objects.select_related("institution", "educational_organization").filter(pk=period_id).first()

    @staticmethod
    def list_by_organization(organization_id, status=None):
        queryset = AcademicPeriod.objects.filter(educational_organization_id=organization_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related("institution", "educational_organization").order_by("-starts_at")

    @staticmethod
    def list_by_institution(institution_id, status=None):
        queryset = AcademicPeriod.objects.filter(institution_id=institution_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related("institution", "educational_organization").order_by("-starts_at")


class CourseOfferingRepository:
    @staticmethod
    def get_by_id(offering_id):
        return CourseOffering.objects.select_related(
            "institution", "educational_organization", "academic_unit", "programme", "academic_period", "subject"
        ).filter(pk=offering_id).first()

    @staticmethod
    def list_by_programme(programme_id, status=None):
        queryset = CourseOffering.objects.filter(programme_id=programme_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related(
            "institution", "educational_organization", "academic_unit", "programme", "academic_period", "subject"
        ).order_by("name")

    @staticmethod
    def list_by_period(period_id, status=None):
        queryset = CourseOffering.objects.filter(academic_period_id=period_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related(
            "institution", "educational_organization", "academic_unit", "programme", "academic_period", "subject"
        ).order_by("name")

    @staticmethod
    def list_by_institution(institution_id, status=None):
        queryset = CourseOffering.objects.filter(institution_id=institution_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related(
            "institution", "educational_organization", "academic_unit", "programme", "academic_period", "subject"
        ).order_by("name")


class ClassGroupRepository:
    @staticmethod
    def get_by_id(class_group_id):
        return ClassGroup.objects.select_related(
            "institution", "educational_organization", "academic_unit", "course_offering"
        ).filter(pk=class_group_id).first()

    @staticmethod
    def list_by_offering(offering_id, status=None):
        queryset = ClassGroup.objects.filter(course_offering_id=offering_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related(
            "institution", "educational_organization", "academic_unit", "course_offering"
        ).order_by("name")

    @staticmethod
    def list_by_institution(institution_id, status=None):
        queryset = ClassGroup.objects.filter(institution_id=institution_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related(
            "institution", "educational_organization", "academic_unit", "course_offering"
        ).order_by("name")


class TeachingAssignmentRepository:
    @staticmethod
    def get_by_id(assignment_id):
        return TeachingAssignment.objects.select_related(
            "institution", "teacher", "class_group", "course_offering", "subject"
        ).filter(pk=assignment_id).first()

    @staticmethod
    def list_by_teacher(teacher_id, status=None):
        queryset = TeachingAssignment.objects.filter(teacher_id=teacher_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related(
            "institution", "teacher", "class_group", "course_offering", "subject"
        ).order_by("-effective_from")

    @staticmethod
    def list_by_class_group(class_group_id, status=None):
        queryset = TeachingAssignment.objects.filter(class_group_id=class_group_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related(
            "institution", "teacher", "class_group", "course_offering", "subject"
        ).order_by("-effective_from")

    @staticmethod
    def list_by_institution(institution_id, status=None):
        queryset = TeachingAssignment.objects.filter(institution_id=institution_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related(
            "institution", "teacher", "class_group", "course_offering", "subject"
        ).order_by("-effective_from")

    @staticmethod
    def get_active_assignment(teacher_id, class_group_id, when=None):
        when = when or timezone.now()
        return TeachingAssignment.objects.filter(
            teacher_id=teacher_id,
            class_group_id=class_group_id,
            status=TeachingAssignmentStatus.ACTIVE,
            effective_from__lte=when,
        ).filter(Q(effective_until__isnull=True) | Q(effective_until__gt=when)).first()