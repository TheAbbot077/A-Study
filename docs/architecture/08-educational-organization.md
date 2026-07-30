# PI-8C.1 — Institutional Organization & Educational Authority Platform

## Strategic Objective

Extend the AI University Operating System from a learner-centric platform into a governed institutional platform by introducing durable organizational structures, educational authority, class organization, teaching assignments, and capability-based permissions.

## Core Design Principle

Educational organizations do not exist to store users. Educational organizations exist to organize educational authority.

Every new object answers: "Who has legitimate educational authority to perform this action?"

## Educational Organization Model

### Hierarchy

```
Institution
↓
EducationalOrganization
↓
AcademicUnit
↓
Programme
↓
AcademicPeriod
↓
CourseOffering
↓
ClassGroup
↓
TeachingAssignment
↓
Institution-Governed Learning Journey
```

### Aggregates

#### EducationalOrganization

Represents an educational operating structure within an institution.

**Examples:** University, Faculty, School, Campus, College, Division

**Key Fields:**
- institution (FK)
- parent (self-referential FK for hierarchy)
- name, slug, organization_type
- status (active, suspended, archived)
- version (optimistic concurrency)

**Lifecycle:** activation, suspension, archival

#### AcademicUnit

Represents academic subdivisions.

**Examples:** Department of Biology, School of Medicine, Faculty of Business

**Key Fields:**
- institution (FK)
- educational_organization (FK)
- parent (self-referential FK for hierarchy)
- name, slug, unit_type
- status, version

**Owns:** programmes, course offerings

#### Programme

Represents governed educational programmes.

**Examples:** BSc Computer Science, Cambridge A Level, Bachelor of Nursing

**Key Fields:**
- institution (FK)
- educational_organization (FK)
- academic_unit (FK)
- name, slug, qualification, description
- status (draft, active, suspended, archived)
- version

**Lifecycle:** Durable programme lifecycle

#### AcademicPeriod

Represents governed teaching periods.

**Examples:** 2026 Semester 1, 2026 Semester 2, Term 1

**Key Fields:**
- institution (FK)
- educational_organization (FK)
- name, slug, period_type
- starts_at, ends_at
- status (upcoming, open, closed, archived)
- version

**Constraint:** Immutable once closed

#### CourseOffering

Represents delivery of a subject inside a programme during an academic period.

**Conceptually:** Programme + Subject + Academic Period

**Examples:** BIO101, Advanced Calculus, Organic Chemistry

**Key Fields:**
- institution (FK)
- educational_organization (FK)
- academic_unit (FK)
- programme (FK)
- academic_period (FK)
- subject (FK)
- name, slug, description
- status, version

**Uniqueness:** programme + academic_period + subject

#### ClassGroup

Represents actual learner teaching groups.

**Examples:** BIO101 Group A, Form 5 Blue, Engineering Tutorial B

**Key Fields:**
- institution (FK)
- educational_organization (FK)
- academic_unit (FK)
- course_offering (FK)
- name, slug, description
- status (draft, active, suspended, archived, completed)
- version

**Contains:** teachers, learners, lifecycle

#### TeachingAssignment

Teaching authority must always be explicit. Never infer authority because a user belongs to an institution.

**Governs:** Teacher → Class Group → Course Offering → Subject → Effective Dates → Capabilities

**Key Fields:**
- institution (FK)
- teacher (FK to User)
- class_group (FK)
- course_offering (FK)
- subject (FK)
- effective_from, effective_until
- status (pending, active, suspended, expired)
- version

**Lifecycle:** assignment, reassignment, expiry, activation, suspension

**Uniqueness:** teacher + class_group + effective_from

## Capability-Based Educational Authority

### Capability Model

Avoid role-driven authorization. Introduce educational capabilities.

**Capability Codes:**
- INSTITUTION_VIEW_OVERVIEW
- INSTITUTION_MANAGE_USERS
- INSTITUTION_MANAGE_ORGANIZATIONS
- ACADEMIC_MANAGE_PROGRAMMES
- ACADEMIC_MANAGE_COURSES
- ACADEMIC_MANAGE_CLASSES
- ACADEMIC_MANAGE_PERIODS
- ACADEMIC_ASSIGN_TEACHERS
- ACADEMIC_ASSIGN_LEARNERS
- ACADEMIC_VIEW_ANALYTICS
- TEACHER_VIEW_ASSIGNED_CLASSES
- TEACHER_ASSIGN_WORK
- TEACHER_VIEW_PROGRESS
- TEACHER_CREATE_INTERVENTION
- LEARNER_VIEW_CLASS
- LEARNER_VIEW_ASSIGNMENTS

### Role Bundles

Roles become capability bundles:

**Institution Head:**
- institution.view_overview
- institution.manage_users
- institution.manage_organizations
- academic.manage_programmes
- academic.manage_courses
- academic.manage_classes
- academic.manage_periods
- academic.assign_teachers
- academic.assign_learners
- academic.view_analytics

**Academic Dean:**
- academic.manage_programmes
- academic.manage_courses
- academic.manage_classes
- academic.manage_periods
- academic.assign_teachers
- academic.assign_learners
- academic.view_analytics

**Head of Department:**
- academic.manage_programmes
- academic.manage_courses
- academic.manage_classes
- academic.assign_teachers
- academic.view_analytics

**Teacher:**
- teacher.view_assigned_classes
- teacher.assign_work
- teacher.view_progress
- teacher.create_intervention

**Teaching Assistant:**
- teacher.view_assigned_classes
- teacher.assign_work
- teacher.view_progress

**Tutor:**
- teacher.view_assigned_classes
- teacher.view_progress

**Learner:**
- learner.view_class
- learner.view_assignments

### Authorization Rules

**Membership grants almost no instructional authority.**

**Examples:**
- Biology Teacher ✔ assigned Biology classes, ✘ Physics classes
- Department Head ✔ Biology programmes/classes/teachers, ✘ Mathematics department
- Institution Head ✔ institution oversight/staffing/analytics, ✘ unrestricted learner academic privacy
- Platform Superuser ✔ operational support/platform health/administrative tooling, ✘ unrestricted educational privacy

## UserCapability Model

Capabilities are institution-scoped and time-bounded.

**Key Fields:**
- user (FK)
- institution (FK)
- capability_code
- granted_at
- granted_by (FK to User)
- expires_at (nullable for permanent capabilities)
- metadata

**Uniqueness:** user + institution + capability_code

**Property:** is_active (checks expiration)

## Educational Authority Rules

### Privacy

Institutional authority must never expose:
- private Abbot conversations
- private self-study reflections
- Ariel teaching history
- mentor memory
- unrelated learner journals

Teachers should only access information permitted by their teaching assignments.

Institution heads should receive organizational information rather than unrestricted learner detail.

### Audit

Audit:
- organization creation
- academic unit lifecycle
- programme changes
- class creation
- teacher assignment
- learner enrollment
- capability changes
- administrative overrides

Audit remains immutable.

## Events

Durable business events with identifier-only payloads:

- EducationalOrganizationCreated
- AcademicUnitCreated
- ProgrammeActivated
- AcademicPeriodOpened
- CourseOfferingCreated
- ClassGroupCreated
- TeacherAssigned
- TeacherUnassigned
- LearnerEnrolled
- LearnerWithdrawn
- TeachingAssignmentActivated
- TeachingAssignmentExpired

Events remain idempotent.

## APIs

Backend APIs for:
- Educational Organizations
- Academic Units
- Programmes
- Academic Periods
- Course Offerings
- Class Groups
- Teaching Assignments
- Capability inspection
- Assignment history
- Activation, suspension, archival

**No dashboards. No frontend endpoints.**

## Django Admin

Operational administration supporting:
- activation, suspension, archival
- assignment inspection
- capability inspection
- membership inspection
- organizational hierarchy
- audit visibility

## Learning Journey Integration

Institution-governed learning journeys support references to:
- Educational Organization
- Academic Unit
- Programme
- Academic Period
- Course Offering
- Class Group
- Teaching Assignment

**Do not duplicate learning journey ownership. Do not redesign learning journeys.**

## Compatibility

This increment does not alter:
- self-study workflows
- Ariel architecture
- Study Lab architecture
- evidence architecture
- mastery
- competency progression
- remediation
- assessment
- retrieval
- curriculum governance

It establishes institutional authority only.

## Non-Goals

Explicitly exclude:
- dashboards
- frontend
- lesson planning
- Ariel
- Study Lab
- assessment redesign
- remediation redesign
- timetable scheduling
- attendance
- grading
- certificates
- transcripts

These belong to later increments.

## Files Introduced

```
backend/apps/educational_organization/
├── __init__.py
├── apps.py
├── admin.py
├── signals.py
├── domain/
│   ├── __init__.py
│   ├── models.py          # All domain models
│   ├── capabilities.py    # Capability codes and role bundles
│   └── events.py          # Domain events
├── infrastructure/
│   ├── __init__.py
│   └── repositories.py    # Query repositories
├── services/
│   ├── __init__.py
│   ├── organization_service.py      # Aggregate services
│   └── authorization_service.py     # Capability resolution
├── api/
│   ├── __init__.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── tests/
│   ├── __init__.py
│   └── test_educational_organization_api.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
└── management/
    ├── __init__.py
    └── commands/
        ├── __init__.py
        └── setup_educational_capabilities.py
```

## Validation

Manual validation commands:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend pytest backend/apps/institutions
docker compose exec backend pytest backend/apps/learning_journeys
docker compose exec backend pytest
```

## Success Criteria

PI-8C.1 is complete when:

- [x] Educational Organization is introduced as the institutional governance layer
- [x] Academic Units support durable hierarchy
- [x] Programmes and Academic Periods are operational
- [x] Course Offerings and Class Groups are governed
- [x] Teaching Assignments become the canonical source of instructional authority
- [x] Capability-based authorization replaces role assumptions for educational actions
- [x] Institution-governed Learning Journeys integrate without duplication
- [x] Events, APIs, Django Admin, audit, documentation, and regression tests are complete
- [x] Existing self-study and learning journey behaviour remains unchanged
- [x] No frontend implementation is introduced
- [x] The platform is fully prepared for PI-8C.2