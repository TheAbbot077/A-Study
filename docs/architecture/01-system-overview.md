```md
# System Overview

Abbot Study is organized as a modular AI-native education operating system.

## Major System Areas

### Backend

The backend is responsible for:

- authentication
- user roles
- subjects
- documents
- curriculum
- ordered learning progression
- assessments
- Ariel memory
- analytics
- admin operations
- AI orchestration

### Frontend

The frontend is responsible for:

- student dashboard
- subject workspace
- learning interface
- The Abbot experience
- Ariel interface
- assessments
- progress tracking
- admin command center

### Infrastructure

Infrastructure supports:

- PostgreSQL
- Redis
- Celery
- file storage
- Docker development
- staging deployment
- production deployment

## Core Invariant

Learning progression must be deterministic, ordered, and mastery-based.

AI may enrich learning, but it must not secretly control official learning order.