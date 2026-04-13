from django.test import TestCase
from config.models import Funding, ResearcherProfile
from django.contrib.auth import get_user_model

User = get_user_model()


class FundingTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="researcher",
            email="res@test.com",
            password="Testpass123!"
        )

        self.profile = ResearcherProfile.objects.create(user=self.user)

    def test_create_funding(self):
        funding = Funding.objects.create(
            researcher=self.profile,
            title="Test Grant",
            amount=10000,
            status="awarded"
        )

        self.assertEqual(funding.title, "Test Grant")
        self.assertEqual(funding.amount, 10000)

    def test_soft_delete(self):
        funding = Funding.objects.create(
            researcher=self.profile,
            title="Test Grant",
            amount=10000
        )

        funding.soft_delete()

        self.assertTrue(funding.is_deleted)