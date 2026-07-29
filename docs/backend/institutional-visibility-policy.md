# Institutional Visibility Policy

Institutional visibility is explicit.

Institution-visible information includes:

- journey state;
- assigned competencies;
- progress summary;
- required interventions;
- completion readiness.

Learner-private information must not be exposed through institutional APIs:

- private notes;
- reflection drafts;
- private study preferences;
- mentor memory;
- private Learning Identity context.

`InstitutionalJourneyVisibilityPolicy` governs API visibility. It permits the learner, superusers, and institution staff roles with explicit institutional membership.

The policy deliberately returns operational progress and assignment state, not raw learner memory or hidden governance internals.
