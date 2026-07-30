import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.educational_organization.api.serializers import (
    AcademicPeriodSerializer,
    AcademicUnitSerializer,
    ClassGroupSerializer,
    CourseOfferingSerializer,
    EducationalOrganizationSerializer,
    ProgrammeSerializer,
    TeachingAssignmentSerializer,
)
from apps.educational_organization.domain.models import EducationalOrganization, AcademicUnit, Programme, AcademicPeriod, CourseOffering, ClassGroup, TeachingAssignment, UserCapability
from apps.users.domain.models import Institution, User, InstitutionMembership


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def institution(db):
    return Institution.objects.create(
        name="Test University",
        slug="test-university",
        institution_type="university",
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(email="admin@test.com", password="testpass123")


@pytest.fixture
def institution_owner(institution, user):
    return InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role="institution_owner",
    )


@pytest.fixture
def capability(institution, user):
    return UserCapability.objects.create(
        user=user,
        institution=institution,
        capability_code="institution.view_overview",
    )


@pytest.mark.django_db
def test_list_organizations(api_client, institution, user, institution_owner, capability):
    """Test listing educational organizations."""
    api_client.force_authenticate(user=user)
    url = reverse("educational_organization:list_organizations", kwargs={"institution_id": institution.id})
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_create_organization(api_client, institution, user, institution_owner):
    """Test creating an educational organization."""
    # Grant capability
    UserCapability.objects.create(
        user=user,
        institution=institution,
        capability_code="institution.manage_organizations",
    )
    
    api_client.force_authenticate(user=user)
    url = reverse("educational_organization:create_organization", kwargs={"institution_id": institution.id})
    data = {
        "name": "Faculty of Science",
        "slug": "faculty-science",
        "organization_type": "faculty",
    }
    response = api_client.post(url, data)
    assert response.status_code == 201
    assert EducationalOrganization.objects.count() == 1


@pytest.mark.django_db
def test_list_units(api_client, institution, user, institution_owner, capability):
    """Test listing academic units."""
    organization = EducationalOrganization.objects.create(
        institution=institution,
        name="Faculty of Science",
        slug="faculty-science",
        organization_type="faculty",
    )
    
    api_client.force_authenticate(user=user)
    url = reverse("educational_organization:list_units", kwargs={"organization_id": organization.id})
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_create_unit(api_client, institution, user, institution_owner):
    """Test creating an academic unit."""
    # Grant capability
    UserCapability.objects.create(
        user=user,
        institution=institution,
        capability_code="academic.manage_programmes",
    )
    
    organization = EducationalOrganization.objects.create(
        institution=institution,
        name="Faculty of Science",
        slug="faculty-science",
        organization_type="faculty",
    )
    
    api_client.force_authenticate(user=user)
    url = reverse("educational_organization:create_unit", kwargs={"organization_id": organization.id})
    data = {
        "name": "Department of Biology",
        "slug": "dept-biology",
        "unit_type": "department",
    }
    response = api_client.post(url, data)
    assert response.status_code == 201
    assert AcademicUnit.objects.count() == 1


@pytest.mark.django_db
def test_list_programmes(api_client, institution, user, institution_owner, capability):
    """Test listing programmes."""
    organization = EducationalOrganization.objects.create(
        institution=institution,
        name="Faculty of Science",
        slug="faculty-science",
        organization_type="faculty",
    )
    unit = AcademicUnit.objects.create(
        institution=institution,
        educational_organization=organization,
        name="Department of Biology",
        slug="dept-biology",
        unit_type="department",
    )
    
    api_client.force_authenticate(user=user)
    url = reverse("educational_organization:list_programmes", kwargs={"unit_id": unit.id})
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_create_programme(api_client, institution, user, institution_owner):
    """Test creating a programme."""
    # Grant capability
    UserCapability.objects.create(
        user=user,
        institution=institution,
        capability_code="academic.manage_programmes",
    )
    
    organization = EducationalOrganization.objects.create(
        institution=institution,
        name="Faculty of Science",
        slug="faculty-science",
        organization_type="faculty",
    )
    unit = AcademicUnit.objects.create(
        institution=institution,
        educational_organization=organization,
        name="Department of Biology",
        slug="dept-biology",
        unit_type="department",
    )
    
    api_client.force_authenticate(user=user)
    url = reverse("educational_organization:create_programme", kwargs={"unit_id": unit.id})
    data = {
        "name": "BSc Biology",
        "slug": "bsc-biology",
        "qualification": "Bachelor of Science",
    }
    response = api_client.post(url, data)
    assert response.status_code == 201
    assert Programme.objects.count() == 1


@pytest.mark.django_db
def test_unauthorized_access(api_client, institution, user):
    """Test unauthorized access without capability."""
    api_client.force_authenticate(user=user)
    url = reverse("educational_organization:list_organizations", kwargs={"institution_id": institution.id})
    response = api_client.get(url)
    assert response.status_code == 403