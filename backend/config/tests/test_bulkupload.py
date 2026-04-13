from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()


class BulkUploadFullTests(TestCase):

    def save(self, *args, **kwargs):
        if self.user_type == 'researcher' and self.approval_status == 'approved':
            self.is_staff = True
        elif self.user_type == 'admin' or self.is_superuser:
            self.is_staff = True
        else:
            self.is_staff = False

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="pass"
        )

        # 🔥 FORCE EVERYTHING BEFORE SAVE
        self.admin.user_type = "admin"
        self.admin.approval_status = "approved"
        self.admin.is_staff = True
        self.admin.is_superuser = True   # 🔥 ADD THIS
        self.admin.save()

        self.client.force_login(self.admin)

        # student
        self.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="pass"
        )
        self.student.user_type = "student"
        self.student.approval_status = "approved"
        self.student.save()
        
    # ✅ 1. Admin access allowed
    def test_admin_can_upload(self):
        self.client.force_login(self.admin)

        file = SimpleUploadedFile("test.xml", b"<root></root>", content_type="text/xml")

        response = self.client.post("/bulk-upload/", {"files": [file]})

        self.assertNotEqual(response.status_code, 403)

    # ❌ 2. Non-admin blocked
    def test_student_cannot_upload(self):
        self.client.force_login(self.student)

        file = SimpleUploadedFile("test.xml", b"<root></root>")

        response = self.client.post("/bulk-upload/", {"files": [file]})

        self.assertEqual(response.status_code, 403)

    # ❌ 3. No file
    def test_no_file(self):
        self.client.force_login(self.admin)

        response = self.client.post("/bulk-upload/", {})

        self.assertEqual(response.status_code, 400)
        self.assertIn("No files provided", str(response.content))

    # ❌ 4. Non XML file
    def test_non_xml_file(self):
        self.client.force_login(self.admin)

        file = SimpleUploadedFile("test.txt", b"invalid")

        response = self.client.post("/bulk-upload/", {"files": [file]})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Only XML files are allowed", str(response.content))

    # ❌ 5. Large file
    def test_large_file(self):
        self.client.force_login(self.admin)

        big_content = b"x" * (6 * 1024 * 1024)
        file = SimpleUploadedFile("big.xml", big_content)

        response = self.client.post("/bulk-upload/", {"files": [file]})

        self.assertEqual(response.status_code, 200)
        self.assertIn("File too large", str(response.content))

    # ✅ 6. Valid XML upload (mock parser)
    @patch("config.views.parse_xml_funding")
    @patch("config.views.parse_xml_projects")
    @patch("config.views.parse_xml_publications")
    def test_valid_xml_upload(self, mock_pub, mock_proj, mock_funding):
        self.client.force_login(self.admin)

        mock_pub.return_value = 1
        mock_proj.return_value = 1
        mock_funding.return_value = 1

        xml_content = b"""
        <root>
            <section label="Research Funding History"></section>
        </root>
        """

        file = SimpleUploadedFile("valid.xml", xml_content, content_type="text/xml")

        response = self.client.post("/bulk-upload/", {"files": [file]})

        self.assertEqual(response.status_code, 200)
        self.assertIn("success", str(response.content).lower())

    # ✅ 7. Multiple files upload
    def test_multiple_files(self):
        self.client.force_login(self.admin)

        file1 = SimpleUploadedFile("file1.xml", b"<root></root>")
        file2 = SimpleUploadedFile("file2.txt", b"invalid")

        response = self.client.post("/bulk-upload/", {"files": [file1, file2]})

        self.assertEqual(response.status_code, 200)

    # ❌ 8. Invalid XML structure
    def test_invalid_xml_structure(self):
        self.client.force_login(self.admin)

        file = SimpleUploadedFile("bad.xml", b"<root><invalid></root>")

        response = self.client.post("/bulk-upload/", {"files": [file]})

        self.assertEqual(response.status_code, 200)