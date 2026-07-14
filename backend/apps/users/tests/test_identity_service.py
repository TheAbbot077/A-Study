from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.domain.models import Profile, User
from apps.users.services.identity_service import IdentityService


class IdentityServiceTests(TestCase):
    def setUp(self):
        self.service = IdentityService()

    def test_get_current_identity_creates_missing_profile(self):
        user = User.objects.create_user(email="legacy@example.com", password="secret12345")

        identity = self.service.get_current_identity(user)

        profile = Profile.objects.get(user=user)
        self.assertEqual(identity["profile"]["display_name"], "legacy")
        self.assertEqual(profile.display_name, "legacy")

    def test_get_current_identity_does_not_overwrite_existing_profile(self):
        user = User.objects.create_user(email="existing@example.com", password="secret12345")
        profile = Profile.objects.create(user=user, display_name="Existing Name")

        identity = self.service.get_current_identity(user)

        profile.refresh_from_db()
        self.assertEqual(identity["profile"]["display_name"], "Existing Name")
        self.assertEqual(profile.display_name, "Existing Name")

    def test_get_current_identity_is_idempotent_for_missing_profile(self):
        user = User.objects.create_user(email="repeat@example.com", password="secret12345")

        first_identity = self.service.get_current_identity(user)
        second_identity = self.service.get_current_identity(user)

        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
        self.assertEqual(first_identity["profile"], second_identity["profile"])

    def test_register_user_creates_exactly_one_profile(self):
        user = self.service.register_user(
            email="registered@example.com",
            password="secret12345",
            display_name="Registered User",
        )

        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
        self.assertEqual(Profile.objects.get(user=user).display_name, "Registered User")


class IdentityApiProfileInvariantTests(APITestCase):
    def setUp(self):
        self.password = "secret12345"

    def test_login_repairs_missing_profile(self):
        user = User.objects.create_user(email="login@example.com", password=self.password)

        response = self.client.post(
            "/api/auth/login/",
            {"email": user.email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], user.email)
        self.assertEqual(response.data["profile"]["display_name"], "login")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_current_identity_repairs_missing_profile(self):
        user = User.objects.create_user(email="me@example.com", password=self.password)
        self.client.force_authenticate(user)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], user.email)
        self.assertEqual(response.data["profile"]["display_name"], "me")
        self.assertTrue(Profile.objects.filter(user=user).exists())
