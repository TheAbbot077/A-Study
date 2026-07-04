# Identity Platform

## Purpose

Identity is the platform capability responsible for knowing who a user is, what account they belong to, what institution they are connected to, and what roles they hold.

## Core Principle

Authentication is not the whole identity system. Authentication proves who someone is; Identity describes who they are within Abbot Study.

## What Identity Owns

- users
- profiles
- institution memberships
- roles
- account lifecycle
- session-facing identity
- identity-related audit events

## What Identity Does Not Own

- learning progress
- curriculum
- documents
- assessments
- The Abbot
- Ariel
- billing
- notifications

## User Is Not Profile

The User model owns authentication and authorization essentials, while Profile owns personal display and preference information. These concerns should remain distinct even when they are closely related.

## Institution-Aware From Day One

The platform must eventually support schools, universities, companies, professional academies, and individual learners. Identity must therefore be designed to support multi-tenant and institution-aware contexts from the start.

## Roles Before Fine-Grained Permissions

Phase 2A introduces stable roles first as Django TextChoices. Fine-grained permissions may come later once the core identity model is established and validated.

## Identity Events

Identity publishes business events for account lifecycle and profile changes, but it does not decide which downstream services or handlers react to them. The event layer is intentionally decoupled from any specific consumer.

Future identity events include:

- UserRegistered
- UserLoggedIn
- UserLoggedOut
- ProfileUpdated
- InstitutionCreated
- InstitutionMembershipCreated
- RoleAssigned
- RoleRemoved

## Dependency Rules

- Other domains may reference Identity.
- Identity should avoid importing learning, curriculum, assessment, or AI domains.
- Identity may publish Business Events.
- Identity must not call AI providers.

## Future Extensions

The identity platform may later support:

- SSO
- institution onboarding
- teacher accounts
- parent/guardian accounts
- alumni accounts
- enterprise identity providers
- audit trails
