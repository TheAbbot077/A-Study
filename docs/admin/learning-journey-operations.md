# Learning Journey Operations Admin

The Django admin provides a read-safe operational console for learning journeys.

Journey admin includes read-only sections for:

- source bindings;
- subject bindings;
- action receipts;
- operations;
- integrity findings;
- competency progress.

Service-backed actions:

- synchronize selected journeys;
- run integrity check;
- run safe recovery;
- pause selected journeys;
- resume selected journeys;
- archive eligible journeys;
- evaluate institutional completion;
- generate institutional intervention recommendations.

Admin actions call application services. They do not directly edit governed lifecycle fields or mutate learning authority.

