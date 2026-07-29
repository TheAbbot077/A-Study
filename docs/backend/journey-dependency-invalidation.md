# Journey dependency invalidation

The self-study dependency order is:

```text
intent
→ curriculum resolution
→ curriculum selection
→ subject binding
→ diagnostic
→ placement
→ bridge plan
→ learning plan
→ teaching preparation
→ teaching session
```

PI-8B.2 documents invalidation through `SelfStudyJourneyDependencyInvalidationPolicy`.

The policy does not delete historical records. It identifies which downstream capability references become obsolete when upstream intent data changes. Source bounded contexts remain responsible for superseding, invalidating, or replacing their own records.

Current executable intent revision is intentionally disabled until the source intent revision command can safely apply these invalidation plans.
