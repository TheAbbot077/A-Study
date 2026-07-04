# Users App

The Users app owns Identity Platform concerns for Abbot Study.

## Responsibilities

- Authentication-facing user records
- Profiles
- Institution memberships
- Roles
- Identity-related account lifecycle concerns

## Non-responsibilities

The Users app does not own learning progress, curriculum, documents, assessments, AI behavior, billing, or notifications.

## Structure Guidance

- Business logic should live in services.
- Database models should live in domain/models.py when introduced.
- API views should live under api.

## Profile Note

The Users app now includes a separate Profile model for display and preference information. Profile is distinct from User, which remains focused on authentication and authorization essentials.

## Institution Note

The Users app also defines Institution and InstitutionMembership as part of the Identity Platform foundation. These models capture institution ownership and membership relationships without introducing permissions or broader domain logic yet.

## Role and Institution Type Constants

The identity foundation now uses Django TextChoices for stable role and institution type values. Institution roles and institution types are defined as reusable constants for future domain logic and UI integration.

## API Note

The Users app now includes a lightweight identity API surface for registration, login, logout, and current-user retrieval. These endpoints coordinate through the identity service and use session-based authentication.

## Event Note

Registration publishes an identity.user_registered business event through EventPublisher. The identity layer emits the event after user and profile creation succeeds, but it does not decide which downstream consumers react to the event.
