# Learning Journey Security Checklist

PI-8B release checks must cover:

- tenant isolation on journey collection, detail, progress, actions, operations, integrity, and institutional endpoints;
- object-level authorization through journey authority providers;
- actor-specific serialization via view policy;
- private evidence body exclusion;
- mentor-memory exclusion;
- raw diagnostic answer exclusion;
- raw concept-check response exclusion;
- task payload identifier-only discipline;
- event payload identifier-only discipline;
- log payload safety;
- admin read-only lifecycle and authority fields;
- idempotency replay safety;
- idempotency payload mismatch rejection;
- optimistic version conflict behavior;
- bounded batch command scope;
- no recovery path that fabricates authority, subject bindings, evidence, mastery, or completion.

Each checklist item maps to code policy, tests, integrity diagnostics, or documented operational controls. It is not a substitute for manual security review before production rollout.

