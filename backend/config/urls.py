"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.api.urls')),
    path('api/storage/', include('apps.storage.api.urls')),
    path('api/academic/', include('apps.academic.api.urls')),
    path('api/assessments/', include('apps.assessments.api.urls')),
    path('api/learning/', include('apps.learning.api.urls')),
    path('api/remediation/', include('apps.remediation.api.urls')),
    path('api/assessment-review/', include('apps.assessment_review.api.urls')),
    path('api/content-intelligence/', include('apps.content_intelligence.api.urls')),
    path('api/content-processing/', include('apps.content_processing.api.urls')),
    path('api/academic-review/', include('apps.academic_review.api.urls')),
    path('api/retrieval/', include('apps.retrieval.api.urls')),
    path('api/self-study/', include('apps.self_study.api.urls')),
    path('api/curricula/', include('apps.self_study.api.public_curriculum_urls')),
    path('api/curriculum-registry/', include('apps.self_study.api.curriculum_urls')),
]
