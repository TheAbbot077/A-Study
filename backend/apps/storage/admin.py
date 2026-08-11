from django.contrib import admin

from apps.storage.domain.models import StoredFile


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "original_filename",
        "owner",
        "tenant",
        "security_scope",
        "provider",
        "size_bytes",
        "created_at",
    ]
    list_filter = ["security_scope", "provider", "created_at"]
    search_fields = ["id", "original_filename", "stored_filename", "owner__email", "tenant__name"]
    readonly_fields = [
        "id",
        "original_filename",
        "stored_filename",
        "content_type",
        "size_bytes",
        "checksum",
        "provider",
        "owner",
        "tenant",
        "security_scope",
        "created_at",
        "updated_at",
    ]
