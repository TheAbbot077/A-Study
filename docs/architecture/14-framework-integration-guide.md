# Framework Integration Guide

## Purpose

Abbot Study adapts frameworks to its architecture rather than allowing framework defaults to dictate the long-term system design. This keeps the product aligned with its own layered, domain-oriented structure.

## Core Principle

We adapt frameworks to our architecture, not our architecture to framework defaults.

## Django Model Discovery

Django expects app models to be importable from apps/<app>/models.py. This is the conventional discovery point for model registration and app loading.

## Domain Model Location

Abbot Study keeps real domain model implementations in apps/<app>/domain/models.py. This preserves a domain-oriented structure and keeps application concerns separated from framework-specific discovery wiring.

## Django Bridge Pattern

The project uses a bridge pattern for Django model discovery:

apps/<app>/models.py imports and re-exports models from apps/<app>/domain/models.py.

Example:

from apps.users.domain.models import User

__all__ = ["User"]

## Why This Exists

The bridge allows Django to discover models while preserving the domain-oriented project structure. It keeps framework integration thin and avoids mixing framework conventions directly into the domain implementation.

## Required Rule

Every Django app that owns database models must have:

- domain/models.py for the real model implementation
- models.py as the Django discovery bridge

## Future Adapter Examples

This pattern may be extended to other integration points, including:

- Celery task discovery
- Next.js route discovery
- AI provider adapters
- storage provider adapters
- notification provider adapters
- authentication provider adapters

## Safety Rule

Framework adapters should stay thin. They should not contain business logic.
