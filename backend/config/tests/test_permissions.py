from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class PermissionTests(TestCase):

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="Testpass123!",
            user_type="admin",
            approval_status="approved"
        )

        self.admin.user_type = "admin"
        self.admin.approval_status = "approved"
        self.admin.is_staff = True   # ← IMPORTANT
        self.admin.save()

        self.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="Testpass123!",
            user_type="student",
            approval_status="approved"
        )

    def test_admin_access(self):
        self.client.login(email="admin@test.com", password="Testpass123!")

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_student_redirect(self):
        self.client.login(email="student@test.com", password="Testpass123!")

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)