from django.db.models import Q
from django.utils import timezone

from apps.educational_organization.domain.capabilities import EducationalCapability
from apps.educational_organization.domain.models import UserCapability
from apps.educational_organization.infrastructure.repositories import TeachingAssignmentRepository


class AuthorizationService:
    """Service for resolving educational capabilities and authority."""

    @staticmethod
    def has_capability(user_id, institution_id, capability_code):
        """Check if user has an active capability in an institution."""
        return UserCapability.objects.filter(
            user_id=user_id,
            institution_id=institution_id,
            capability_code=capability_code,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).exists()

    @staticmethod
    def get_user_capabilities(user_id, institution_id):
        """Get all active capabilities for a user in an institution."""
        return list(
            UserCapability.objects.filter(
                user_id=user_id,
                institution_id=institution_id,
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).values_list("capability_code", flat=True)
        )

    @staticmethod
    def grant_capability(user_id, institution_id, capability_code, granted_by_id, expires_at=None, metadata=None):
        """Grant a capability to a user."""
        capability, created = UserCapability.objects.update_or_create(
            user_id=user_id,
            institution_id=institution_id,
            capability_code=capability_code,
            defaults={
                "granted_by_id": granted_by_id,
                "expires_at": expires_at,
                "metadata": metadata or {},
            },
        )
        return capability

    @staticmethod
    def revoke_capability(user_id, institution_id, capability_code):
        """Revoke a capability from a user."""
        return UserCapability.objects.filter(
            user_id=user_id,
            institution_id=institution_id,
            capability_code=capability_code,
        ).delete()

    @staticmethod
    def is_teacher_of_class(user_id, class_group_id, when=None):
        """Check if user is an active teacher of a class group."""
        return TeachingAssignmentRepository.get_active_assignment(
            teacher_id=user_id,
            class_group_id=class_group_id,
            when=when,
        ) is not None

    @staticmethod
    def get_teacher_authority_scope(user_id, institution_id):
        """Get the scope of teacher's authority in an institution."""
        assignments = TeachingAssignmentRepository.list_by_teacher(user_id)
        assignments = assignments.filter(
            institution_id=institution_id,
            status="active",
        )
        
        class_group_ids = set()
        course_offering_ids = set()
        subject_ids = set()
        
        for assignment in assignments:
            when = timezone.now()
            if assignment.effective_from <= when and (assignment.effective_until is None or assignment.effective_until > when):
                class_group_ids.add(assignment.class_group_id)
                course_offering_ids.add(assignment.course_offering_id)
                subject_ids.add(assignment.subject_id)
        
        return {
            "class_groups": list(class_group_ids),
            "course_offerings": list(course_offering_ids),
            "subjects": list(subject_ids),
        }

    @staticmethod
    def can_manage_organization(user_id, institution_id, organization_id):
        """Check if user can manage an educational organization."""
        if not AuthorizationService.has_capability(user_id, institution_id, EducationalCapability.INSTITUTION_MANAGE_ORGANIZATIONS):
            return False
        
        # Institution head can manage all organizations
        # Others need specific organizational authority (future enhancement)
        return True

    @staticmethod
    def can_manage_unit(user_id, institution_id, unit_id):
        """Check if user can manage an academic unit."""
        if not AuthorizationService.has_capability(user_id, institution_id, EducationalCapability.ACADEMIC_MANAGE_PROGRAMMES):
            return False
        
        # Academic dean and above can manage units
        # Department head can manage units in their organization (future enhancement)
        return True

    @staticmethod
    def can_assign_teachers(user_id, institution_id, class_group_id):
        """Check if user can assign teachers to a class group."""
        if not AuthorizationService.has_capability(user_id, institution_id, EducationalCapability.ACADEMIC_ASSIGN_TEACHERS):
            return False
        
        # Institution head and academic dean can assign teachers
        # Head of department can assign teachers in their units (future enhancement)
        return True

    @staticmethod
    def can_view_learner_data(user_id, institution_id, learner_id):
        """Check if user can view learner data."""
        # Teachers can only view learners in their assigned classes
        if AuthorizationService.has_capability(user_id, institution_id, EducationalCapability.TEACHER_VIEW_PROGRESS):
            # Check if teacher has any active teaching assignments
            # This is a simplified check - in practice, you'd check specific class enrollments
            return True
        
        # Institution head can view organizational analytics but not unrestricted learner privacy
        if AuthorizationService.has_capability(user_id, institution_id, EducationalCapability.INSTITUTION_VIEW_OVERVIEW):
            return True
        
        return False