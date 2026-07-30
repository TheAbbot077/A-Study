from apps.educational_organization.domain.models import (
    AcademicPeriod,
    AcademicUnit,
    ClassGroup,
    CourseOffering,
    EducationalOrganization,
    Programme,
    TeachingAssignment,
)
from apps.educational_organization.infrastructure.repositories import (
    AcademicPeriodRepository,
    AcademicUnitRepository,
    ClassGroupRepository,
    CourseOfferingRepository,
    EducationalOrganizationRepository,
    ProgrammeRepository,
    TeachingAssignmentRepository,
)


class EducationalOrganizationService:
    @staticmethod
    def create_organization(institution_id, name, slug, organization_type, parent_id=None, metadata=None):
        return EducationalOrganization.objects.create(
            institution_id=institution_id,
            name=name,
            slug=slug,
            organization_type=organization_type,
            parent_id=parent_id,
            metadata=metadata or {},
        )

    @staticmethod
    def get_organization(organization_id):
        return EducationalOrganizationRepository.get_by_id(organization_id)

    @staticmethod
    def list_organizations(institution_id, status=None):
        return EducationalOrganizationRepository.list_by_institution(institution_id, status=status)

    @staticmethod
    def archive_organization(organization, when=None):
        organization.archive(when=when)
        organization.save()
        return organization


class AcademicUnitService:
    @staticmethod
    def create_unit(institution_id, organization_id, name, slug, unit_type, parent_id=None, metadata=None):
        return AcademicUnit.objects.create(
            institution_id=institution_id,
            educational_organization_id=organization_id,
            name=name,
            slug=slug,
            unit_type=unit_type,
            parent_id=parent_id,
            metadata=metadata or {},
        )

    @staticmethod
    def get_unit(unit_id):
        return AcademicUnitRepository.get_by_id(unit_id)

    @staticmethod
    def list_units(organization_id, status=None):
        return AcademicUnitRepository.list_by_organization(organization_id, status=status)

    @staticmethod
    def archive_unit(unit, when=None):
        unit.archive(when=when)
        unit.save()
        return unit


class ProgrammeService:
    @staticmethod
    def create_programme(institution_id, organization_id, unit_id, name, slug, qualification="", description="", metadata=None):
        return Programme.objects.create(
            institution_id=institution_id,
            educational_organization_id=organization_id,
            academic_unit_id=unit_id,
            name=name,
            slug=slug,
            qualification=qualification,
            description=description,
            metadata=metadata or {},
        )

    @staticmethod
    def get_programme(programme_id):
        return ProgrammeRepository.get_by_id(programme_id)

    @staticmethod
    def list_programmes(unit_id, status=None):
        return ProgrammeRepository.list_by_unit(unit_id, status=status)

    @staticmethod
    def archive_programme(programme, when=None):
        programme.archive(when=when)
        programme.save()
        return programme


class AcademicPeriodService:
    @staticmethod
    def create_period(institution_id, organization_id, name, slug, period_type, starts_at, ends_at, metadata=None):
        return AcademicPeriod.objects.create(
            institution_id=institution_id,
            educational_organization_id=organization_id,
            name=name,
            slug=slug,
            period_type=period_type,
            starts_at=starts_at,
            ends_at=ends_at,
            metadata=metadata or {},
        )

    @staticmethod
    def get_period(period_id):
        return AcademicPeriodRepository.get_by_id(period_id)

    @staticmethod
    def list_periods(organization_id, status=None):
        return AcademicPeriodRepository.list_by_organization(organization_id, status=status)

    @staticmethod
    def archive_period(period, when=None):
        period.archive(when=when)
        period.save()
        return period


class CourseOfferingService:
    @staticmethod
    def create_offering(institution_id, organization_id, unit_id, programme_id, period_id, subject_id, name, slug, description="", metadata=None):
        return CourseOffering.objects.create(
            institution_id=institution_id,
            educational_organization_id=organization_id,
            academic_unit_id=unit_id,
            programme_id=programme_id,
            academic_period_id=period_id,
            subject_id=subject_id,
            name=name,
            slug=slug,
            description=description,
            metadata=metadata or {},
        )

    @staticmethod
    def get_offering(offering_id):
        return CourseOfferingRepository.get_by_id(offering_id)

    @staticmethod
    def list_offerings(programme_id, status=None):
        return CourseOfferingRepository.list_by_programme(programme_id, status=status)

    @staticmethod
    def archive_offering(offering, when=None):
        offering.archive(when=when)
        offering.save()
        return offering


class ClassGroupService:
    @staticmethod
    def create_class_group(institution_id, organization_id, unit_id, offering_id, name, slug, description="", metadata=None):
        return ClassGroup.objects.create(
            institution_id=institution_id,
            educational_organization_id=organization_id,
            academic_unit_id=unit_id,
            course_offering_id=offering_id,
            name=name,
            slug=slug,
            description=description,
            metadata=metadata or {},
        )

    @staticmethod
    def get_class_group(class_group_id):
        return ClassGroupRepository.get_by_id(class_group_id)

    @staticmethod
    def list_class_groups(offering_id, status=None):
        return ClassGroupRepository.list_by_offering(offering_id, status=status)

    @staticmethod
    def archive_class_group(class_group, when=None):
        class_group.archive(when=when)
        class_group.save()
        return class_group


class TeachingAssignmentService:
    @staticmethod
    def create_assignment(institution_id, teacher_id, class_group_id, offering_id, subject_id, effective_from, effective_until=None, metadata=None):
        return TeachingAssignment.objects.create(
            institution_id=institution_id,
            teacher_id=teacher_id,
            class_group_id=class_group_id,
            course_offering_id=offering_id,
            subject_id=subject_id,
            effective_from=effective_from,
            effective_until=effective_until,
            metadata=metadata or {},
        )

    @staticmethod
    def get_assignment(assignment_id):
        return TeachingAssignmentRepository.get_by_id(assignment_id)

    @staticmethod
    def list_teacher_assignments(teacher_id, status=None):
        return TeachingAssignmentRepository.list_by_teacher(teacher_id, status=status)

    @staticmethod
    def list_class_group_assignments(class_group_id, status=None):
        return TeachingAssignmentRepository.list_by_class_group(class_group_id, status=status)

    @staticmethod
    def activate_assignment(assignment):
        assignment.activate()
        assignment.save()
        return assignment

    @staticmethod
    def suspend_assignment(assignment):
        assignment.suspend()
        assignment.save()
        return assignment

    @staticmethod
    def expire_assignment(assignment):
        assignment.expire()
        assignment.save()
        return assignment