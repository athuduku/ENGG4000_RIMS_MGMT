from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from config.models import ResearcherProfile, Project
from unittest.mock import patch
import json

User = get_user_model()


# ---------------- BULK UPLOAD ----------------
class BulkUploadTests(TestCase):

    def setUp(self):
        self.client = Client()

        # 🔥 CREATE REAL ADMIN (SUPERUSER)
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="pass"
        )

        # 🔥 match your system logic
        self.admin.user_type = "admin"
        self.admin.approval_status = "approved"
        self.admin.save()

        self.client.force_login(self.admin)

    def test_non_xml_file(self):
        file = SimpleUploadedFile("file.txt", b"bad")

        response = self.client.post("/bulk-upload/", {"files": [file]}, 
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertIn("Only XML files are allowed", str(response.content))

    def test_no_file(self):
        response = self.client.post("/bulk-upload/", {})
        self.assertEqual(response.status_code, 400)

    def test_large_file(self):
        big_content = b"x" * (6 * 1024 * 1024)
        file = SimpleUploadedFile("big.xml", big_content)

        response = self.client.post("/bulk-upload/", {"files": [file]})

        self.assertEqual(response.status_code, 200)
        self.assertIn("File too large", str(response.content))

    def test_multiple_files(self):
        file1 = SimpleUploadedFile("file1.xml", b"<root></root>")
        file2 = SimpleUploadedFile("file2.txt", b"bad")

        response = self.client.post("/bulk-upload/", {"files": [file1, file2]})

        self.assertEqual(response.status_code, 200)

    @patch("config.views.parse_xml_funding")
    @patch("config.views.parse_xml_projects")
    @patch("config.views.parse_xml_publications")
    def test_valid_xml_upload(self, mock_pub, mock_proj, mock_funding):
        mock_pub.return_value = 1
        mock_proj.return_value = 1
        mock_funding.return_value = 1

        xml = b"""
        <root>
            <section label="Research Funding History"></section>
        </root>
        """

        file = SimpleUploadedFile("test.xml", xml, content_type="text/xml")

        response = self.client.post("/bulk-upload/", {"files": [file]})

        self.assertEqual(response.status_code, 200)
        self.assertIn("success", str(response.content).lower())


# ---------------- STUDENT UPLOAD ----------------
class StudentUploadTests(TestCase):

    def setUp(self):
        self.client = Client()

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass"
        )

        self.student.user_type = "student"
        self.student.approval_status = "approved"
        self.student.save()

        self.client.force_login(self.student)

    def test_wrong_owner(self):
        xml = b"""
        <generic-cv>
            <section label="Personal Information">
                <section label="Identification">
                    <field label="First Name">
                        <value>Wrong</value>
                    </field>
                    <field label="Family Name">
                        <value>User</value>
                    </field>
                </section>
                <section label="Email">
                    <field label="Email Address">
                        <value>wrong@test.com</value>
                    </field>
                </section>
            </section>
            <section label="Activities">
                <section label="Presentations"></section>
            </section>
            <section label="Publications">
                <section label="Journal Articles"></section>
            </section>
        </generic-cv>
        """

        file = SimpleUploadedFile("test.xml", xml, content_type="text/xml")

        response = self.client.post("/student/upload-ccv/", {"files": [file]})

        self.assertEqual(response.status_code, 403)


# ---------------- API TESTS ----------------
class APITests(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="researcher1",
            email="r@test.com",
            password="pass"
        )

        self.user.user_type = "researcher"
        self.user.approval_status = "approved"
        self.user.save()

        self.researcher = ResearcherProfile.objects.create(user=self.user)

        self.project = Project.objects.create(
            researcher=self.researcher,
            title="Test Project"
        )

        self.client.force_login(self.user)

    def test_update_project_status(self):
        response = self.client.post(
            f"/api/projects/{self.project.id}/update-status/",
            data=json.dumps({"status": "completed"}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

    def test_invalid_status(self):
        response = self.client.post(
            f"/api/projects/{self.project.id}/update-status/",
            data=json.dumps({"status": "invalid"}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)