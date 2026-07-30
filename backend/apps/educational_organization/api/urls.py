from django.urls import path

from apps.educational_organization.api import views


app_name = "educational_organization"

urlpatterns = [
    # Educational Organizations
    path("institutions/<uuid:institution_id>/organizations/", views.list_organizations, name="list_organizations"),
    path("institutions/<uuid:institution_id>/organizations/create/", views.create_organization, name="create_organization"),
    # Academic Units
    path("organizations/<uuid:organization_id>/units/", views.list_units, name="list_units"),
    path("organizations/<uuid:organization_id>/units/create/", views.create_unit, name="create_unit"),
    # Programmes
    path("units/<uuid:unit_id>/programmes/", views.list_programmes, name="list_programmes"),
    path("units/<uuid:unit_id>/programmes/create/", views.create_programme, name="create_programme"),
    # Academic Periods
    path("organizations/<uuid:organization_id>/periods/", views.list_periods, name="list_periods"),
    path("organizations/<uuid:organization_id>/periods/create/", views.create_period, name="create_period"),
    # Course Offerings
    path("programmes/<uuid:programme_id>/offerings/", views.list_offerings, name="list_offerings"),
    path("programmes/<uuid:programme_id>/offerings/create/", views.create_offering, name="create_offering"),
    # Class Groups
    path("offerings/<uuid:offering_id>/class-groups/", views.list_class_groups, name="list_class_groups"),
    path("offerings/<uuid:offering_id>/class-groups/create/", views.create_class_group, name="create_class_group"),
    # Teaching Assignments
    path("class-groups/<uuid:class_group_id>/teaching-assignments/", views.list_teaching_assignments, name="list_teaching_assignments"),
    path("class-groups/<uuid:class_group_id>/teaching-assignments/create/", views.create_teaching_assignment, name="create_teaching_assignment"),
]