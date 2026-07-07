# Academic Domain Hardening

## Status
Accepted

## Context

PI-3K closes the Academic Domain before PI-4 Learning Engine begins. ASEM v2 requires business logic to remain in services, domain models to define business concepts, Django `models.py` to remain a discovery bridge, and meaningful business actions to publish events.

The Academic Domain already includes structure, resources, content, ingestion tracking, importer contracts, manual authoring, quality review, APIs, and admin integration.

## Decision

We will treat the Academic Domain as complete for PI-3 once the hardening review and human Docker validation are complete.

The hardening pass keeps the existing architecture:

* adapters delegate mutations to services
* services persist domain model changes
* services publish academic business events
* importers produce proposals and do not persist
* `apps.academic.models` remains a Django discovery bridge
* Learning Engine, Assessment, AI, parser improvements, and frontend work remain deferred

We will harden Django admin so mutable admin form saves delegate to services, direct deletes are disabled, and ResourceIngestionJob records are not directly mutated through generic admin forms.

We will register and test all academic event names for EventRegistry discoverability.

## Consequences

* PI-4 can depend on a stable Academic Domain layer.
* Admin and API adapters follow the same service-boundary rule.
* Direct admin deletes cannot bypass archive-oriented services.
* Academic events remain discoverable before subscribers are attached.
* Resource ingestion lifecycle changes remain explicit service/API operations.
* No Learning Engine, assessment, parser, AI, or frontend feature work is introduced by PI-3K.
