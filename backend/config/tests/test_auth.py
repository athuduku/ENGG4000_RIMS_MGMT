from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.signup_url = "/signup/"
        self.login_url = "/login/"
        self.dashboard_url = "/dashboard/"
        self.password = "Test@12345"

    def test_signup_creates_user(self):
        response = self.client.post(self.signup_url, {
            "name": "John Doe",
            "email": "john@example.com",
            "password": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="john@example.com").exists())

    def test_login_requires_approval(self):
        user = User.objects.create_user(
            username="John Doe",
            email="john@example.com",
            password=self.password,
            approval_status="pending"
        )

        response = self.client.post(self.login_url, {
            "email": user.email,
            "password": self.password
        })
        self.assertEqual(response.status_code, 403)  

    def test_login_success_for_approved_user(self):
        user = User.objects.create_user(
            username="Approved User",
            email="approved@example.com",
            password=self.password,
            approval_status="approved"
        )

        response = self.client.post(self.login_url, {
            "email": user.email,
            "password": self.password
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("redirect", response.json()) 
