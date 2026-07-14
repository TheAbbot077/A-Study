from rest_framework import serializers

from apps.storage.domain.models import StoredFile


class StoredFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredFile
        fields = [
            "id",
            "original_filename",
            "stored_filename",
            "content_type",
            "size_bytes",
            "checksum",
            "provider",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class StoredFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True, allow_empty_file=False)
