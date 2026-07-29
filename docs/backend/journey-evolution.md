# Journey Evolution

PI-8B.3 adds a journey evolution layer over the governed `LearningJourney` backbone.

`JourneyEvolutionService` reacts after competency progression. It does not replace the existing journey lifecycle or self-study orchestration. Its role is to synchronize the journey projection, publish a `journey.evolved` event, and request learning-plan evolution when newly available competencies appear.

## Unlock policy

`CompetencyUnlockPolicy` uses the governed curriculum graph. A downstream competency becomes available only when all required prerequisite `CurriculumEdge` records are satisfied by demonstrated or reinforced competency progress.

Subject-specific rules are not hard-coded. The curriculum graph remains the authority for prerequisites.

## Learning-plan evolution

`LearningPlanEvolutionService` currently emits `learning_plan.evolution_requested` with the journey, triggering competency, and newly unlocked competencies.

This is intentionally an extension point. PI-8B.3 does not rewrite planning algorithms; it gives planning services a governed trigger to remove completed objectives, append newly available objectives, or request replanning.

## Regression and supersession

Regression is allowed only through governed mastery signals such as contradictory evidence. It is never driven by inactivity or elapsed time.

Supersession marks a competency as `SUPERSEDED`, optionally links a successor competency, and preserves historical progress. Curriculum authority changes should evolve the journey without erasing the learner's previous work.
