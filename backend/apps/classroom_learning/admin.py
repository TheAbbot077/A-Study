from django.contrib import admin

from .domain.models import (
    ArielPreparednessAttempt,
    ClassPreparednessAssignment,
    LessonPreparation,
    LessonPrerequisite,
    LearnerPreparednessParticipation,
    PreparednessActivity,
    PreparednessPrompt,
)

admin.site.register(LessonPreparation)
admin.site.register(LessonPrerequisite)
admin.site.register(PreparednessActivity)
admin.site.register(PreparednessPrompt)
admin.site.register(ClassPreparednessAssignment)
admin.site.register(LearnerPreparednessParticipation)
admin.site.register(ArielPreparednessAttempt)
