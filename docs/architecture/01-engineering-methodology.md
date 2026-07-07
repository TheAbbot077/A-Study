# 01 - Engineering Methodology

## Abbot Study Engineering Methodology (ASEM v2)

### Philosophy

Architecture drives implementation.

Frameworks adapt to the architecture.

Business domains are built on reusable platform capabilities.

---

# Engineering Principles

1. Domain-first design.
2. Framework independence.
3. Event-driven architecture.
4. Single responsibility for every capability.
5. Docker is the single source of truth.
6. Tests validate behavior, not implementation details.
7. Human architects define system behavior; AI assists implementation.

---

# Development Lifecycle

Every capability follows the same lifecycle.

## 1. Program Increment Charter

Defines:

* Mission
* Scope
* Dependencies
* Success criteria
* Exit criteria

---

## 2. Capability Contract

Defines:

* Purpose
* Responsibilities
* Non-goals
* Domain objects
* Services
* Events

---

## 3. Design Checkpoint

Review:

* Domain model
* Service boundaries
* Event model
* Dependencies
* APIs
* Architectural impact

---

## 4. Scoped Master Prompt

One capability.

One responsibility.

One implementation scope.

---

## 5. AI-Assisted Implementation

Copilot/OpenCode functions as a junior engineer.

AI may:

* Generate boilerplate
* Implement contracts
* Produce tests
* Draft documentation
* Refactor repetitive code

AI may not independently redefine:

* Product philosophy
* Learning rules
* Domain model philosophy
* Security architecture
* Educational invariants

---

## 6. Docker Validation

Docker is the authoritative development environment.

Validation includes:

* Django system checks
* Migration verification
* Automated test suite
* Targeted capability tests

---

## 7. Architecture Review

Each capability is reviewed for:

* Domain purity
* Event completeness
* Documentation
* ADR updates
* Service boundaries
* Migration quality
* Test coverage

---

## 8. Capability Commit

One capability.

One validated commit.

One architectural milestone.

---

## 9. Program Increment Review

At the completion of every Program Increment:

* Integration review
* Architecture review
* Documentation review
* Technical debt assessment
* Version tag

---

# Domain Design Rules

* Business logic belongs in services.
* Domain models define business concepts.
* Django models.py serves as a discovery bridge.
* Framework-specific concerns remain outside the domain.

---

# Event Philosophy

Business events are first-class architectural components.

Every meaningful business action should publish a business event.

Events must describe business facts rather than technical implementation.

---

# Testing Philosophy

Tests verify business behavior.

Prefer service-level testing.

Avoid brittle implementation-coupled tests.

Mock external dependencies, not business rules.

---

# Documentation Standards

Every capability includes:

* Architecture documentation
* ADR
* Capability tests
* Validation instructions

Documentation evolves with the architecture.

---

# Success Metric

The architecture should become easier to extend after every Program Increment.

# Documentation Maintenance Rule

Constitutional documents are living architectural references.

Upon completion of every Capability or Program Increment, engineering documentation shall be updated to:

mark completed work as complete;
update capability status;
move completed items from "Planned" to "Implemented";
update dependency diagrams where applicable;
preserve architectural rationale;
never rewrite historical ADR decisions;
never alter constitutional principles unless explicitly directed by the project architect.