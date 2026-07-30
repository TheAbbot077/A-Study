from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.educational_organization.api.serializers import (
    AcademicPeriodSerializer,
    AcademicUnitSerializer,
    ClassGroupSerializer,
    CourseOfferingSerializer,
    EducationalOrganizationSerializer,
    ProgrammeSerializer,
    TeachingAssignmentSerializer,
)
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
from apps.educational_organization.services.authorization_service import AuthorizationService
from apps.educational_organization.services.organization_service import (
    AcademicPeriodService,
    AcademicUnitService,
    ClassGroupService,
    CourseOfferingService,
    EducationalOrganizationService,
    ProgrammeService,
    TeachingAssignmentService,
)


# Educational Organizations

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_organizations(request, institution_id):
    """List educational organizations for an institution."""
    if not AuthorizationService.has_capability(request.user.id, institution_id, "institution.view_overview"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    organizations = EducationalOrganizationService.list_organizations(institution_id)
    serializer = EducationalOrganizationSerializer(organizations, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_organization(request, institution_id):
    """Create a new educational organization."""
    if not AuthorizationService.has_capability(request.user.id, institution_id, "institution.manage_organizations"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    data = request.data
    organization = EducationalOrganizationService.create_organization(
        institution_id=institution_id,
        name=data["name"],
        slug=data["slug"],
        organization_type=data["organization_type"],
        parent_id=data.get("parent_id"),
        metadata=data.get("metadata"),
    )
    serializer = EducationalOrganizationSerializer(organization)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# Academic Units

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_units(request, organization_id):
    """List academic units for an organization."""
    organization = EducationalOrganizationRepository.get_by_id(organization_id)
    if not organization:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, organization.institution_id, "institution.view_overview"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    units = AcademicUnitService.list_units(organization_id)
    serializer = AcademicUnitSerializer(units, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_unit(request, organization_id):
    """Create a new academic unit."""
    organization = EducationalOrganizationRepository.get_by_id(organization_id)
    if not organization:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, organization.institution_id, "academic.manage_programmes"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    data = request.data
    unit = AcademicUnitService.create_unit(
        institution_id=organization.institution_id,
        organization_id=organization_id,
        name=data["name"],
        slug=data["slug"],
        unit_type=data["unit_type"],
        parent_id=data.get("parent_id"),
        metadata=data.get("metadata"),
    )
    serializer = AcademicUnitSerializer(unit)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# Programmes

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_programmes(request, unit_id):
    """List programmes for an academic unit."""
    unit = AcademicUnitRepository.get_by_id(unit_id)
    if not unit:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, unit.institution_id, "institution.view_overview"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    programmes = ProgrammeService.list_programmes(unit_id)
    serializer = ProgrammeSerializer(programmes, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_programme(request, unit_id):
    """Create a new programme."""
    unit = AcademicUnitRepository.get_by_id(unit_id)
    if not unit:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, unit.institution_id, "academic.manage_programmes"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    data = request.data
    programme = ProgrammeService.create_programme(
        institution_id=unit.institution_id,
        organization_id=unit.educational_organization_id,
        unit_id=unit_id,
        name=data["name"],
        slug=data["slug"],
        qualification=data.get("qualification", ""),
        description=data.get("description", ""),
        metadata=data.get("metadata"),
    )
    serializer = ProgrammeSerializer(programme)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# Academic Periods

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_periods(request, organization_id):
    """List academic periods for an organization."""
    organization = EducationalOrganizationRepository.get_by_id(organization_id)
    if not organization:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, organization.institution_id, "institution.view_overview"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    periods = AcademicPeriodService.list_periods(organization_id)
    serializer = AcademicPeriodSerializer(periods, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_period(request, organization_id):
    """Create a new academic period."""
    organization = EducationalOrganizationRepository.get_by_id(organization_id)
    if not organization:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, organization.institution_id, "academic.manage_periods"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    data = request.data
    period = AcademicPeriodService.create_period(
        institution_id=organization.institution_id,
        organization_id=organization_id,
        name=data["name"],
        slug=data["slug"],
        period_type=data["period_type"],
        starts_at=data["starts_at"],
        ends_at=data["ends_at"],
        metadata=data.get("metadata"),
    )
    serializer = AcademicPeriodSerializer(period)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# Course Offerings

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_offerings(request, programme_id):
    """List course offerings for a programme."""
    programme = ProgrammeRepository.get_by_id(programme_id)
    if not programme:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, programme.institution_id, "institution.view_overview"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    offerings = CourseOfferingService.list_offerings(programme_id)
    serializer = CourseOfferingSerializer(offerings, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_offering(request, programme_id):
    """Create a new course offering."""
    programme = ProgrammeRepository.get_by_id(programme_id)
    if not programme:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, programme.institution_id, "academic.manage_courses"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    data = request.data
    offering = CourseOfferingService.create_offering(
        institution_id=programme.institution_id,
        organization_id=programme.educational_organization_id,
        unit_id=programme.academic_unit_id,
        programme_id=programme_id,
        period_id=data["academic_period_id"],
        subject_id=data["subject_id"],
        name=data["name"],
        slug=data["slug"],
        description=data.get("description", ""),
        metadata=data.get("metadata"),
    )
    serializer = CourseOfferingSerializer(offering)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# Class Groups

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_class_groups(request, offering_id):
    """List class groups for a course offering."""
    offering = CourseOfferingRepository.get_by_id(offering_id)
    if not offering:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, offering.institution_id, "institution.view_overview"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    class_groups = ClassGroupService.list_class_groups(offering_id)
    serializer = ClassGroupSerializer(class_groups, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_class_group(request, offering_id):
    """Create a new class group."""
    offering = CourseOfferingRepository.get_by_id(offering_id)
    if not offering:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, offering.institution_id, "academic.manage_classes"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    data = request.data
    class_group = ClassGroupService.create_class_group(
        institution_id=offering.institution_id,
        organization_id=offering.educational_organization_id,
        unit_id=offering.academic_unit_id,
        offering_id=offering_id,
        name=data["name"],
        slug=data["slug"],
        description=data.get("description", ""),
        metadata=data.get("metadata"),
    )
    serializer = ClassGroupSerializer(class_group)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# Teaching Assignments

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_teaching_assignments(request, class_group_id):
    """List teaching assignments for a class group."""
    class_group = ClassGroupRepository.get_by_id(class_group_id)
    if not class_group:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, class_group.institution_id, "academic.assign_teachers"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    assignments = TeachingAssignmentService.list_class_group_assignments(class_group_id)
    serializer = TeachingAssignmentSerializer(assignments, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_teaching_assignment(request, class_group_id):
    """Create a new teaching assignment."""
    class_group = ClassGroupRepository.get_by_id(class_group_id)
    if not class_group:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not AuthorizationService.has_capability(request.user.id, class_group.institution_id, "academic.assign_teachers"):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    data = request.data
    assignment = TeachingAssignmentService.create_assignment(
        institution_id=class_group.institution_id,
        teacher_id=data["teacher_id"],
        class_group_id=class_group_id,
        offering_id=class_group.course_offering_id,
        subject_id=data["subject_id"],
        effective_from=data["effective_from"],
        effective_until=data.get("effective_until"),
        metadata=data.get("metadata"),
    )
    serializer = TeachingAssignmentSerializer(assignment)
    return Response(serializer.data, status=status.HTTP_201_CREATED)