from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTests(TestCase):

    def test_create_user(self):
        user = User.objects.create_user(
            username="ashok",
            email="ashok@test.com",
            password="Testpass123!"
        )

        self.assertEqual(user.email, "ashok@test.com")
        self.assertTrue(user.check_password("Testpass123!"))

    def test_email_unique(self):
        User.objects.create_user(
            username="user1",
            email="same@test.com",
            password="Testpass123!"
        )

        with self.assertRaises(Exception):
            User.objects.create_user(
                username="user2",
                email="same@test.com",
                password="Testpass123!"
            )

    def test_staff_flag_logic(self):
        user = User.objects.create_user(
            username="researcher",
            email="res@test.com",
            password="Testpass123!",
            user_type="researcher",
            approval_status="approved"
        )

        user.save()
        self.assertTrue(user.is_staff)