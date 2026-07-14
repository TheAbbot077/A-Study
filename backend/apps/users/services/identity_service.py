from django.utils.text import slugify

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import Institution, InstitutionMembership, InstitutionRole, InstitutionType, Profile, User


class IdentityService:
    def __init__(self, event_publisher: EventPublisher | None = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def _default_display_name_for_user(self, user: User) -> str:
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = None

        if profile and getattr(profile, "display_name", "").strip():
            return profile.display_name.strip()

        username = getattr(user, "username", "")
        if isinstance(username, str) and username.strip():
            return username.strip()

        email = (user.email or "").strip()
        if "@" in email:
            local_part = email.split("@", 1)[0].strip()
            if local_part:
                return local_part

        return email

    def ensure_profile(self, user: User, display_name: str | None = None) -> Profile:
        normalized_display_name = (display_name or "").strip() or self._default_display_name_for_user(user)
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={"display_name": normalized_display_name},
        )

        if created:
            return profile

        if normalized_display_name and not profile.display_name.strip():
            profile.display_name = normalized_display_name
            profile.save(update_fields=["display_name", "updated_at"])

        return profile

    def register_user(self, email: str, password: str, display_name: str = "") -> User:
        user = User.objects.create_user(email=email, password=password)
        self.ensure_profile(user, display_name=display_name)
        institution_name = display_name.strip() or email.split("@")[0]
        institution = Institution.objects.create(
            name=f"{institution_name}'s Study Space",
            slug=f"{slugify(institution_name) or 'learner'}-{str(user.id)[:8]}",
            institution_type=InstitutionType.INDIVIDUAL,
        )
        InstitutionMembership.objects.create(
            user=user,
            institution=institution,
            role=InstitutionRole.STUDENT,
            is_active=True,
        )

        self.event_publisher.publish(
            BusinessEvent.create(
                "identity.user_registered",
                payload={"user_id": str(user.id), "email": user.email},
            )
        )
        return user

    def get_current_identity(self, user: User) -> dict:
        profile = self.ensure_profile(user)
        memberships = InstitutionMembership.objects.select_related("institution").filter(user=user, is_active=True).order_by("created_at")
        return {
            "id": str(user.id),
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "profile": {
                "display_name": profile.display_name,
                "timezone": profile.timezone,
                "preferred_language": profile.preferred_language,
            },
            "institutions": [
                {
                    "id": str(membership.institution_id),
                    "name": membership.institution.name,
                    "slug": membership.institution.slug,
                    "role": membership.role,
                    "institution_type": membership.institution.institution_type,
                }
                for membership in memberships
            ],
        }
