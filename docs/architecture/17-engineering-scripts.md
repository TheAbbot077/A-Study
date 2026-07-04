# Engineering Validation Scripts

## Purpose

These PowerShell scripts standardize common Docker-based validation and maintenance workflows for Abbot Study.

## Docker as the Source of Truth

The scripts use the existing Docker Compose environment for validation. They do not create local virtual environments, install dependencies, or bypass the containerized runtime.

## When to Use Each Script

- `validate_backend.ps1`: run backend system checks, migration drift checks, and pytest from the container.
- `validate_frontend.ps1`: run frontend lint, typecheck, and build from the container.
- `validate_all.ps1`: run the backend and frontend validation scripts in sequence.
- `docker_reset.ps1`: stop, rebuild, and restart the Docker environment.
- `docker_logs.ps1`: print recent logs for backend, celery, frontend, postgres, and redis.

## Why Copilot or Codex Should Not Run Tests Automatically

Automated agents should not run tests by default unless explicitly instructed. Validation workflows are environment-sensitive and can be slow or disruptive. Keeping them explicit preserves clarity, control, and developer intent.
