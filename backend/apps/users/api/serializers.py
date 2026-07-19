from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.users.domain.models import Profile, User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    display_name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError("Password is required.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["display_name", "timezone", "preferred_language"]


class CurrentUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    institutions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "is_staff", "is_superuser", "profile", "institutions"]

    def get_institutions(self, obj):
        memberships = obj.institutionmembership_set.filter(is_active=True).select_related("institution").order_by("institution__name", "role")
        return [{"id": str(item.institution_id), "name": item.institution.name, "slug": item.institution.slug, "role": item.role, "institution_type": item.institution.institution_type} for item in memberships]
