import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.academic.domain.models import Subject
from apps.users.domain.models import Institution


class EducationalOrganizationStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"


class AcademicUnitStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"


class ProgrammeStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"


class AcademicPeriodStatus(models.TextChoices):
    UPCOMING = "upcoming", "Upcoming"
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    ARCHIVED = "archived", "Archived"


class CourseOfferingStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"


class ClassGroupStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"
    COMPLETED = "completed", "Completed"


class TeachingAssignmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    EXPIRED = "expired", "Expired"


class EducationalOrganization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="educational_organizations")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    organization_type = models.CharField(max_length=100)
    status = models.CharField(max_length=32, choices=EducationalOrganizationStatus.choices, default=EducationalOrganizationStatus.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "educational_organization"
        indexes = [
            models.Index(fields=["institution", "status"], name="edu_org_inst_status_idx"),
            models.Index(fields=["parent"], name="edu_org_parent_idx"),
            models.Index(fields=["slug"], name="edu_org_slug_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["institution", "slug"], name="unique_edu_org_institution_slug"),
            models.UniqueConstraint(fields=["institution", "name"], name="unique_edu_org_institution_name"),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError("Organization cannot be its own parent.", code="SELF_REFERENCING_PARENT")
        if self.parent_id and self.parent.institution_id != self.institution_id:
            raise ValidationError("Parent organization must belong to the same institution.", code="PARENT_INSTITUTION_MISMATCH")

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == EducationalOrganizationStatus.ARCHIVED and not self.archived_at:
            self.archived_at = timezone.now()
        return super().save(*args, **kwargs)

    def archive(self, *, when=None) -> bool:
        if self.status == EducationalOrganizationStatus.ARCHIVED:
            return False
        self.status = EducationalOrganizationStatus.ARCHIVED
        self.archived_at = when or timezone.now()
        self.version += 1
        return True


class AcademicUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="academic_units")
    educational_organization = models.ForeignKey(EducationalOrganization, on_delete=models.PROTECT, related_name="academic_units")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    unit_type = models.CharField(max_length=100)
    status = models.CharField(max_length=32, choices=AcademicUnitStatus.choices, default=AcademicUnitStatus.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "academic_unit"
        indexes = [
            models.Index(fields=["institution", "status"], name="acad_unit_inst_status_idx"),
            models.Index(fields=["educational_organization", "status"], name="acad_unit_org_status_idx"),
            models.Index(fields=["parent"], name="acad_unit_parent_idx"),
            models.Index(fields=["slug"], name="acad_unit_slug_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["educational_organization", "slug"], name="unique_acad_unit_org_slug"),
            models.UniqueConstraint(fields=["educational_organization", "name"], name="unique_acad_unit_org_name"),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError("Academic unit cannot be its own parent.", code="SELF_REFERENCING_PARENT")
        if self.parent_id and self.parent.educational_organization_id != self.educational_organization_id:
            raise ValidationError("Parent unit must belong to the same educational organization.", code="PARENT_ORG_MISMATCH")

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == AcademicUnitStatus.ARCHIVED and not self.archived_at:
            self.archived_at = timezone.now()
        return super().save(*args, **kwargs)

    def archive(self, *, when=None) -> bool:
        if self.status == AcademicUnitStatus.ARCHIVED:
            return False
        self.status = AcademicUnitStatus.ARCHIVED
        self.archived_at = when or timezone.now()
        self.version += 1
        return True


class Programme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="programmes")
    educational_organization = models.ForeignKey(EducationalOrganization, on_delete=models.PROTECT, related_name="programmes")
    academic_unit = models.ForeignKey(AcademicUnit, on_delete=models.PROTECT, related_name="programmes")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    qualification = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=ProgrammeStatus.choices, default=ProgrammeStatus.DRAFT)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "programme"
        indexes = [
            models.Index(fields=["institution", "status"], name="prog_inst_status_idx"),
            models.Index(fields=["academic_unit", "status"], name="prog_unit_status_idx"),
            models.Index(fields=["slug"], name="prog_slug_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["academic_unit", "slug"], name="unique_programme_unit_slug"),
            models.UniqueConstraint(fields=["academic_unit", "name"], name="unique_programme_unit_name"),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == ProgrammeStatus.ARCHIVED and not self.archived_at:
            self.archived_at = timezone.now()
        return super().save(*args, **kwargs)

    def archive(self, *, when=None) -> bool:
        if self.status == ProgrammeStatus.ARCHIVED:
            return False
        self.status = ProgrammeStatus.ARCHIVED
        self.archived_at = when or timezone.now()
        self.version += 1
        return True


class AcademicPeriod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="academic_periods")
    educational_organization = models.ForeignKey(EducationalOrganization, on_delete=models.PROTECT, related_name="academic_periods")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    period_type = models.CharField(max_length=100)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=32, choices=AcademicPeriodStatus.choices, default=AcademicPeriodStatus.UPCOMING)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "academic_period"
        indexes = [
            models.Index(fields=["institution", "status"], name="acad_period_inst_status_idx"),
            models.Index(fields=["educational_organization", "status"], name="acad_period_org_status_idx"),
            models.Index(fields=["slug"], name="acad_period_slug_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["educational_organization", "slug"], name="unique_acad_period_org_slug"),
            models.UniqueConstraint(fields=["educational_organization", "name"], name="unique_acad_period_org_name"),
            models.CheckConstraint(condition=Q(ends_at__gt=models.F("starts_at")), name="acad_period_end_after_start"),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.ends_at <= self.starts_at:
            raise ValidationError("Academic period end must be after start.", code="INVALID_PERIOD_RANGE")

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == AcademicPeriodStatus.ARCHIVED and not self.archived_at:
            self.archived_at = timezone.now()
        return super().save(*args, **kwargs)

    def archive(self, *, when=None) -> bool:
        if self.status == AcademicPeriodStatus.ARCHIVED:
            return False
        self.status = AcademicPeriodStatus.ARCHIVED
        self.archived_at = when or timezone.now()
        self.version += 1
        return True


class CourseOffering(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="course_offerings")
    educational_organization = models.ForeignKey(EducationalOrganization, on_delete=models.PROTECT, related_name="course_offerings")
    academic_unit = models.ForeignKey(AcademicUnit, on_delete=models.PROTECT, related_name="course_offerings")
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="course_offerings")
    academic_period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, related_name="course_offerings")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="course_offerings")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=CourseOfferingStatus.choices, default=CourseOfferingStatus.DRAFT)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "course_offering"
        indexes = [
            models.Index(fields=["institution", "status"], name="co_inst_status_idx"),
            models.Index(fields=["programme", "status"], name="co_prog_status_idx"),
            models.Index(fields=["academic_period", "status"], name="co_period_status_idx"),
            models.Index(fields=["subject"], name="co_subject_idx"),
            models.Index(fields=["slug"], name="co_slug_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["programme", "academic_period", "subject"], name="unique_co_programme_period_subject"),
            models.UniqueConstraint(fields=["programme", "slug"], name="unique_co_programme_slug"),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == CourseOfferingStatus.ARCHIVED and not self.archived_at:
            self.archived_at = timezone.now()
        return super().save(*args, **kwargs)

    def archive(self, *, when=None) -> bool:
        if self.status == CourseOfferingStatus.ARCHIVED:
            return False
        self.status = CourseOfferingStatus.ARCHIVED
        self.archived_at = when or timezone.now()
        self.version += 1
        return True


class ClassGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="class_groups")
    educational_organization = models.ForeignKey(EducationalOrganization, on_delete=models.PROTECT, related_name="class_groups")
    academic_unit = models.ForeignKey(AcademicUnit, on_delete=models.PROTECT, related_name="class_groups")
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="class_groups")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=ClassGroupStatus.choices, default=ClassGroupStatus.DRAFT)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "class_group"
        indexes = [
            models.Index(fields=["institution", "status"], name="cg_inst_status_idx"),
            models.Index(fields=["course_offering", "status"], name="cg_co_status_idx"),
            models.Index(fields=["slug"], name="cg_slug_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["course_offering", "slug"], name="unique_cg_co_slug"),
            models.UniqueConstraint(fields=["course_offering", "name"], name="unique_cg_co_name"),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == ClassGroupStatus.ARCHIVED and not self.archived_at:
            self.archived_at = timezone.now()
        return super().save(*args, **kwargs)

    def archive(self, *, when=None) -> bool:
        if self.status == ClassGroupStatus.ARCHIVED:
            return False
        self.status = ClassGroupStatus.ARCHIVED
        self.archived_at = when or timezone.now()
        self.version += 1
        return True


class TeachingAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="teaching_assignments")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="teaching_assignments")
    class_group = models.ForeignKey(ClassGroup, on_delete=models.PROTECT, related_name="teaching_assignments")
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="teaching_assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="teaching_assignments")
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=TeachingAssignmentStatus.choices, default=TeachingAssignmentStatus.PENDING)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "teaching_assignment"
        indexes = [
            models.Index(fields=["institution", "status"], name="ta_inst_status_idx"),
            models.Index(fields=["teacher", "status"], name="ta_teacher_status_idx"),
            models.Index(fields=["class_group", "status"], name="ta_cg_status_idx"),
            models.Index(fields=["course_offering", "status"], name="ta_co_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "class_group", "effective_from"],
                name="unique_teacher_class_effective_from",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.teacher.email} -> {self.class_group.name}"

    def clean(self):
        super().clean()
        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValidationError("Effective until must be after effective from.", code="INVALID_DATE_RANGE")
        if self.course_offering_id and self.class_group_id and self.course_offering_id != self.class_group.course_offering_id:
            raise ValidationError("Course offering must match class group course offering.", code="COURSE_OFFERING_MISMATCH")
        if self.subject_id and self.course_offering_id and self.subject_id != self.course_offering.subject_id:
            raise ValidationError("Subject must match course offering subject.", code="SUBJECT_MISMATCH")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def activate(self, *, when=None) -> bool:
        if self.status == TeachingAssignmentStatus.ACTIVE:
            return False
        self.status = TeachingAssignmentStatus.ACTIVE
        self.version += 1
        return True

    def suspend(self, *, when=None) -> bool:
        if self.status == TeachingAssignmentStatus.SUSPENDED:
            return False
        self.status = TeachingAssignmentStatus.SUSPENDED
        self.version += 1
        return True

    def expire(self, *, when=None) -> bool:
        if self.status == TeachingAssignmentStatus.EXPIRED:
            return False
        self.status = TeachingAssignmentStatus.EXPIRED
        self.version += 1
        return True


class UserCapability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="capabilities")
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="user_capabilities")
    capability_code = models.CharField(max_length=128)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="granted_capabilities")
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "user_capability"
        indexes = [
            models.Index(fields=["user", "capability_code"], name="uc_user_cap_idx"),
            models.Index(fields=["institution", "capability_code"], name="uc_inst_cap_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "institution", "capability_code"], name="unique_user_institution_capability"),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} : {self.capability_code}"

    @property
    def is_active(self) -> bool:
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True


__all__ = [
    "EducationalOrganization",
    "AcademicUnit",
    "Programme",
    "AcademicPeriod",
    "CourseOffering",
    "ClassGroup",
    "TeachingAssignment",
    "UserCapability",
    "EducationalOrganizationStatus",
    "AcademicUnitStatus",
    "ProgrammeStatus",
    "AcademicPeriodStatus",
    "CourseOfferingStatus",
    "ClassGroupStatus",
    "TeachingAssignmentStatus",
]