# Docker Foundation

## Purpose

Docker is used to provide a predictable development and verification environment for Abbot Study.

## Services

### postgres

PostgreSQL 16 database for application data.

### redis

Redis 7 for caching and Celery background jobs.

### backend

Python 3.12 container prepared for Django.

### frontend

Node 22 container prepared for Next.js.

## Current Phase

During Phase 1B, backend and frontend containers only verify runtime availability.

Django and Next.js are not installed yet.

## Rule

Docker must support deterministic local verification before advanced AI or Codex-assisted development is introduced.