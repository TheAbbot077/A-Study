"""
Management command to setup educational capabilities for institution roles.

This command grants appropriate capabilities to users based on their institution roles.
"""

from django.core.management.base import BaseCommand

from apps.educational_organization.domain.capabilities import EducationalCapability
from apps.educational_organization.services.authorization_service import AuthorizationService
from apps.users.domain.models import InstitutionMembership


class Command(BaseCommand):
    help = "Setup educational capabilities for institution members based on their roles"

    def handle(self, *args, **options):
        self.stdout.write("Setting up educational capabilities...")
        
        role_capability_mapping = {
            "institution_owner": EducationalCapability.get_role_bundle("institution_head"),
            "administrator": EducationalCapability.get_role_bundle("academic_dean"),
            "teacher": EducationalCapability.get_role_bundle("teacher"),
            "reviewer": EducationalCapability.get_role_bundle("teaching_assistant"),
        }
        
        total_updated = 0
        
        for membership in InstitutionMembership.objects.filter(is_active=True):
            capabilities = role_capability_mapping.get(membership.role, [])
            
            for capability_code in capabilities:
                AuthorizationService.grant_capability(
                    user_id=membership.user_id,
                    institution_id=membership.institution_id,
                    capability_code=capability_code,
                    granted_by_id=membership.user_id,  # Self-granted via role
                )
                total_updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully setup {total_updated} capabilities for {InstitutionMembership.objects.filter(is_active=True).count()} users")
        )