from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        r = self.client.post(reverse("signup"), {"username": "newbie", "password1": "Strong-pass-123",
                                                 "password2": "Strong-pass-123"})
        self.assertRedirects(r, reverse("analyses:index"))
        self.assertTrue(User.objects.filter(username="newbie").exists())
        self.assertEqual(self.client.get(reverse("analyses:index")).status_code, 200)

    def test_signup_rejects_mismatched_password(self):
        r = self.client.post(reverse("signup"), {"username": "x", "password1": "Strong-pass-123",
                                                 "password2": "other-pass-456"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="x").exists())

    def test_login_and_logout(self):
        User.objects.create_user("a", password="Strong-pass-123")
        r = self.client.post(reverse("login"), {"username": "a", "password": "Strong-pass-123"})
        self.assertRedirects(r, reverse("analyses:index"))
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("analyses:index")).status_code, 302)

    def test_anonymous_is_blocked(self):
        self.assertRedirects(self.client.get(reverse("analyses:index")),
                             f"{reverse('login')}?next=/")
        self.assertEqual(self.client.get("/api/analyses/").status_code, 403)
