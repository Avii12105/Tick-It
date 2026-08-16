from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile

User = get_user_model()


class ProfileTests(TestCase):
    def test_profile_auto_created_on_user_creation(self):
        user = User.objects.create_user(username="alice", password="pass12345")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.role, Profile.Role.ATTENDEE)

    def test_signup_sets_role_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "org1",
                "email": "org1@example.com",
                "password1": "strongpass123",
                "password2": "strongpass123",
                "role": Profile.Role.ORGANIZER,
            },
        )
        self.assertRedirects(response, reverse("events:home"))
        user = User.objects.get(username="org1")
        self.assertEqual(user.profile.role, Profile.Role.ORGANIZER)

    def test_login_flow(self):
        User.objects.create_user(username="alice", password="pass12345")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": "pass12345"},
        )
        self.assertRedirects(response, reverse("events:home"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_authenticated_user_redirected_away_from_signup(self):
        User.objects.create_user(username="alice", password="pass12345")
        self.client.login(username="alice", password="pass12345")
        response = self.client.get(reverse("accounts:signup"))
        self.assertRedirects(response, reverse("events:home"))