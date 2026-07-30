"""
Signal handlers for educational organization events.

Events are published when domain objects are created or transition states.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.educational_organization.domain.events import (
    AcademicUnitCreated,
    AcademicPeriodOpened,
    ClassGroupCreated,
    CourseOfferingCreated,
    EducationalOrganizationCreated,
    ProgrammeActivated,
    TeacherAssigned,
)
from apps.educational_organization.domain.models import (
    AcademicUnit,
    AcademicPeriod,
    ClassGroup,
    CourseOffering,
    EducationalOrganization,
    Programme,
    TeachingAssignment,
)


@receiver(post_save, sender=EducationalOrganization)
def publish_educational_organization_created(sender, instance, created, **kwargs):
    if created:
        event = EducationalOrganizationCreated(
            organization_id=instance.id,
            institution_id=instance.institution_id,
            name=instance.name,
            organization_type=instance.organization_type,
            parent_id=instance.parent_id,
        )
        # TODO: publish event via event bus
        # event_bus.publish(event)
        pass


@receiver(post_save, sender=AcademicUnit)
def publish_academic_unit_created(sender, instance, created, **kwargs):
    if created:
        event = AcademicUnitCreated(
            unit_id=instance.id,
            institution_id=instance.institution_id,
            organization_id=instance.educational_organization_id,
            name=instance.name,
            unit_type=instance.unit_type,
            parent_id=instance.parent_id,
        )
        # TODO: publish event via event bus
        pass


@receiver(pre_save, sender=Programme)
def publish_programme_activated(sender, instance, **kwargs):
    if instance.pk:
        old = Programme.objects.filter(pk=instance.pk).first()
        if old and old.status != "active" and instance.status == "active":
            event = ProgrammeActivated(
                programme_id=instance.id,
                institution_id=instance.institution_id,
                organization_id=instance.educational_organization_id,
                unit_id=instance.academic_unit_id,
                name=instance.name,
            )
            # TODO: publish event via event bus
            pass


@receiver(pre_save, sender=AcademicPeriod)
def publish_academic_period_opened(sender, instance, **kwargs):
    if instance.pk:
        old = AcademicPeriod.objects.filter(pk=instance.pk).first()
        if old and old.status != "open" and instance.status == "open":
            event = AcademicPeriodOpened(
                period_id=instance.id,
                institution_id=instance.institution_id,
                organization_id=instance.educational_organization_id,
                name=instance.name,
                period_type=instance.period_type,
                starts_at=instance.starts_at,
                ends_at=instance.ends_at,
            )
            # TODO: publish event via event bus
            pass


@receiver(post_save, sender=CourseOffering)
def publish_course_offering_created(sender, instance, created, **kwargs):
    if created:
        event = CourseOfferingCreated(
            offering_id=instance.id,
            institution_id=instance.institution_id,
            organization_id=instance.educational_organization_id,
            unit_id=instance.academic_unit_id,
            programme_id=instance.programme_id,
            period_id=instance.academic_period_id,
            subject_id=instance.subject_id,
            name=instance.name,
        )
        # TODO: publish event via event bus
        pass


@receiver(post_save, sender=ClassGroup)
def publish_class_group_created(sender, instance, created, **kwargs):
    if created:
        event = ClassGroupCreated(
            class_group_id=instance.id,
            institution_id=instance.institution_id,
            organization_id=instance.educational_organization_id,
            unit_id=instance.academic_unit_id,
            offering_id=instance.course_offering_id,
            name=instance.name,
        )
        # TODO: publish event via event bus
        pass


@receiver(pre_save, sender=TeachingAssignment)
def publish_teacher_assigned(sender, instance, **kwargs):
    if instance.pk:
        old = TeachingAssignment.objects.filter(pk=instance.pk).first()
        if old and old.status != "active" and instance.status == "active":
            event = TeacherAssigned(
                assignment_id=instance.id,
                institution_id=instance.institution_id,
                teacher_id=instance.teacher_id,
                class_group_id=instance.class_group_id,
                course_offering_id=instance.course_offering_id,
                subject_id=instance.subject_id,
                effective_from=instance.effective_from,
            )
            # TODO: publish event via event bus
            pass
