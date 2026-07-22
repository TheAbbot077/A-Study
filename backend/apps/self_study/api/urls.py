from rest_framework.routers import DefaultRouter

from .views import SelfStudyIntentViewSet
from .curriculum_views import CurriculumResolutionViewSet
from .graph_views import CurriculumGraphViewSet
from .diagnostic_views import DiagnosticBlueprintViewSet, EntryDiagnosticViewSet
from .evidence_views import EvidenceMappingRunViewSet
from .bridge_views import BridgePlanViewSet, BridgePlanningRunViewSet
from .teaching_views import TeachingPreparationManifestViewSet, TeachingPreparationRunViewSet
from .orchestration_views import TeachingSessionViewSet
from .workspace_views import SelfStudyWorkspaceViewSet

router = DefaultRouter()
router.register("intents", SelfStudyIntentViewSet, basename="self-study-intent")
router.register("curriculum-resolutions", CurriculumResolutionViewSet, basename="curriculum-resolution")
router.register("curriculum-graphs", CurriculumGraphViewSet, basename="curriculum-graph")
router.register("entry-diagnostics", EntryDiagnosticViewSet, basename="entry-diagnostic")
router.register("diagnostic-blueprints", DiagnosticBlueprintViewSet, basename="diagnostic-blueprint")
router.register("evidence-mapping-runs",EvidenceMappingRunViewSet,basename="evidence-mapping-run")
router.register("bridge-planning-runs", BridgePlanningRunViewSet, basename="bridge-planning-run")
router.register("bridge-plans", BridgePlanViewSet, basename="bridge-plan")
router.register("teaching-preparation-runs", TeachingPreparationRunViewSet, basename="teaching-preparation-run")
router.register("teaching-preparations", TeachingPreparationManifestViewSet, basename="teaching-preparation")
router.register("teaching-sessions", TeachingSessionViewSet, basename="teaching-session")
router.register("workspaces", SelfStudyWorkspaceViewSet, basename="self-study-workspace")

urlpatterns = router.urls
