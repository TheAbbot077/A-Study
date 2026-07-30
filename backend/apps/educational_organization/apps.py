from django.apps import AppConfig


class EducationalOrganizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.educational_organization"
    verbose_name = "Educational Organization"

    def ready(self) -> None:
        import apps.educational_organization.signals  # noqa: F401