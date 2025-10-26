from django.test import TestCase
from django.db import connection
from django.contrib.auth import get_user_model

User = get_user_model()

class DatabaseConnectionTests(TestCase):

    def test_database_connection(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        self.assertEqual(result[0], 1)

    def test_user_table_exists(self):
        tables = connection.introspection.table_names()
        self.assertIn(User._meta.db_table, tables)

    def test_can_create_user(self):
        user = User.objects.create_user(
            username="Database Test User",
            email="dbtest@example.com",
            password="Test@12345"
        )
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.email, "dbtest@example.com")
