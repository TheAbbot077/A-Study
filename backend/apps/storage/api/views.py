from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.storage.api.serializers import StoredFileSerializer, StoredFileUploadSerializer
from apps.storage.domain.models import StoredFile
from apps.storage.infrastructure.providers import LocalStorageProvider
from apps.storage.services import StorageService


class StoredFileViewSet(viewsets.GenericViewSet):
    queryset = StoredFile.objects.all().order_by("-created_at")
    serializer_class = StoredFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return StoredFile.objects.all().order_by("-created_at")

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = StoredFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data["file"]
        stored_file = StorageService(provider=LocalStorageProvider()).store_file(
            uploaded_file.file,
            original_filename=uploaded_file.name,
            content_type=uploaded_file.content_type,
        )
        return Response(StoredFileSerializer(stored_file).data, status=status.HTTP_201_CREATED)
