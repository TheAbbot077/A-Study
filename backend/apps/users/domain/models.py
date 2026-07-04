import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.users.infrastructure.managers import UserManager


class InstitutionType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    SCHOOL = "school", "School"
    UNIVERSITY = "university", "University"
    COMPANY = "company", "Company"
    TRAINING_PROVIDER = "training_provider", "Training Provider"
    GOVERNMENT_ACADEMY = "government_academy", "Government Academy"


class InstitutionRole(models.TextChoices):
    STUDENT = "student", "Student"
    TEACHER = "teacher", "Teacher"
    REVIEWER = "reviewer", "Reviewer"
    ADMINISTRATOR = "administrator", "Administrator"
    INSTITUTION_OWNER = "institution_owner", "Institution Owner"
    SYSTEM_ADMINISTRATOR = "system_administrator", "System Administrator"


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=150, blank=True)
    timezone = models.CharField(max_length=64, default="Africa/Maseru")
    preferred_language = models.CharField(max_length=16, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "profile"
        verbose_name_plural = "profiles"

    def __str__(self) -> str:
        return self.display_name or self.user.email


class Institution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    institution_type = models.CharField(
        max_length=50,
        choices=InstitutionType.choices,
        default=InstitutionType.INDIVIDUAL,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "institution"
        verbose_name_plural = "institutions"

    def __str__(self) -> str:
        return self.name


class InstitutionMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=50,
        choices=InstitutionRole.choices,
        default=InstitutionRole.STUDENT,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "institution", "role"],
                name="unique_user_institution_role",
            )
        ]
        verbose_name = "institution membership"
        verbose_name_plural = "institution memberships"

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.institution.name} ({self.role})"
