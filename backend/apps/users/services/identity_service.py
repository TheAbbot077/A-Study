from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import Profile, User


class IdentityService:
    def __init__(self, event_publisher: EventPublisher | None = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def register_user(self, email: str, password: str, display_name: str = "") -> User:
        user = User.objects.create_user(email=email, password=password)
        Profile.objects.create(user=user, display_name=display_name)

        self.event_publisher.publish(
            BusinessEvent.create(
                "identity.user_registered",
                payload={"user_id": str(user.id), "email": user.email},
            )
        )
        return user

    def get_current_identity(self, user: User) -> dict:
        profile = user.profile
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
        }
