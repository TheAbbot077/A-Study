from rest_framework.routers import DefaultRouter

from apps.remediation.api.views import RemediationPlanViewSet

router = DefaultRouter()
router.register("plans", RemediationPlanViewSet, basename="remediation-plan")

urlpatterns = router.urls
