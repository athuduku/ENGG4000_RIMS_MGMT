from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthTests(TestCase):

    def setUp(self):
        self.client = Client()

        self.password = "Testpass123!"

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=self.password,
            approval_status="approved"
        )

    def test_login_success(self):
        response = self.client.post(reverse('login'), {
            "email": "test@example.com",
            "password": self.password
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("redirect", response.json())

    def test_login_pending_user(self):
        pending_user = User.objects.create_user(
            username="pendinguser",
            email="pending@example.com",
            password=self.password,
            approval_status="pending"
        )

        response = self.client.post(reverse('login'), {
            "email": "pending@example.com",
            "password": self.password
        })

        self.assertEqual(response.status_code, 403)
        self.assertIn("pending approval", response.json()["error"])

    def test_login_invalid(self):
        response = self.client.post(reverse('login'), {
            "email": "wrong@example.com",
            "password": "wrongpass"
        })

        self.assertEqual(response.status_code, 401)

    def test_signup_success(self):
        response = self.client.post(reverse('signup'), {
            "name": "Ashok Test",
            "email": "ashok@test.com",
            "password": "Testpass123!",
            "confirm_password": "Testpass123!",
            "consent": "true"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="ashok@test.com").exists())