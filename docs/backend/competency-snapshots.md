# Competency Snapshots

PI-8B.3 introduces read-safe competency snapshots for learner progress.

Snapshots are projections over `LearningCompetencyProgress`; they do not mutate progression state.

## Competency progress snapshot

`CompetencyProgressSnapshotService.execute()` returns:

- completed competencies;
- active competencies;
- emerging competencies;
- review competencies;
- locked competencies;
- next available competencies.

This becomes the primary governed representation of learner progress.

## Journey progress snapshot

`CompetencyProgressSnapshotService.journey_progress()` returns:

- current learning phase;
- active competency;
- next competency;
- blocked competencies;
- available competencies;
- completed competency count.

The projection avoids fake percentages. It represents governed competency evolution rather than time spent, lesson count, or page completion.

## API endpoints

Read endpoints are exposed under learning journeys:

```text
GET /api/learning-journeys/{id}/competencies/
GET /api/learning-journeys/{id}/progress/
GET /api/learning-journeys/{id}/snapshot/
```

There are no direct write endpoints for competency state. Progression occurs through application services after authoritative mastery decisions.
