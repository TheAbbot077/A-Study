# Frontend Architecture

## Purpose

The frontend is a mobile-first Next.js application for learners, admins, The Abbot, Ariel, assessments, and future institutional workflows. It must support clear user journeys, accessible interaction, and incremental feature growth without unnecessary complexity.

## Core Principle

The frontend must be predictable, accessible, mobile-first, and feature-organized. Shared concerns should be centralized so the UI remains consistent as the product expands.

## Folder Structure

The frontend should follow a clear structure:

- src/app for application routes and global shell wiring.
- src/features for feature-oriented modules such as auth, dashboard, learning, curriculum, assessments, Ariel, Abbot, and admin.
- src/components/ui for reusable presentational primitives.
- src/components/layout for shell and layout composition.
- src/components/feedback for loading, error, and empty states.
- src/services/api for shared API communication.
- src/services/auth for authentication-related service concerns.
- src/hooks for reusable hooks.
- src/lib for utilities and shared helpers.
- src/styles for shared styles when needed.
- src/themes for design tokens and theme layers.
- src/types for shared type definitions.
- src/utils for general-purpose helpers.

## Feature Rule

Features own domain-specific UI and logic. Shared components go under components. This keeps feature modules focused while preserving reusable building blocks.

## API Rule

Do not call fetch directly inside random components. All backend communication should go through the shared API client unless there is a strong documented reason.

## Theme Rule

Visual design should use design tokens and CSS variables. Do not hardcode repeated colors, spacing, shadows, or radii across components.

## Accessibility Rule

Reusable components should use semantic HTML, accessible labels, and appropriate ARIA roles where useful. The experience must remain usable across devices and assistive technologies.

## Mobile-First Rule

Learner-facing screens should be designed for mobile before desktop. Core flows must work well on smaller screens before enhancements for larger displays.

## Error/Loading/Empty State Rule

Every data-driven screen should have clear loading, error, and empty states. These states should be consistent and reusable.

## AI UI Rule

Future AI features like The Abbot, Ariel, oral examiner, and Learning Twin should be implemented as feature modules and should not bypass the shared API client.

## Copilot/Codex Rule

Copilot and Codex may implement scoped frontend tasks but must not reorganize the frontend architecture without explicit instruction.
