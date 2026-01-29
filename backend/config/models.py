from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from django.conf import settings

USER_TYPES = [
    ('admin', 'Admin'),
    ('researcher', 'Researcher'),
    ('student', 'Student'),
]

class CustomUser(AbstractUser):
    username = models.CharField(max_length=150, unique=False, null=True, blank=True)
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    organization = models.CharField(max_length=100, blank=True, null=True)
    consent_to_share = models.BooleanField(default=False)
    approval_status = models.CharField(max_length=20, default='pending')

    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username'] 

    def __str__(self):
        return f"{self.username} ({self.user_type})"


class ResearcherProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ccv_identifier = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    sex = models.CharField(max_length=20, blank=True, null=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    residency_status = models.CharField(max_length=100, blank=True, null=True)
    research_interests = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class Education(models.Model):
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    degree_type = models.CharField(max_length=100, blank=True, null=True)
    specialization = models.CharField(max_length=255, blank=True, null=True)
    institution = models.CharField(max_length=255, blank=True, null=True)
    thesis_title = models.TextField(blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    expected_date = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.degree_type or 'Unknown'} at {self.institution or 'N/A'}"


class Recognition(models.Model):
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.organization})"


class Funding(models.Model):
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    funding_type = models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    start_date = models.CharField(max_length=20, blank=True, null=True)
    end_date = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.title


class Patent(models.Model):
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    number = models.CharField(max_length=100, blank=True, null=True)
    year_issued = models.CharField(max_length=10, blank=True, null=True)
    inventors = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.title


class ResearchSpecialization(models.Model):
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    keyword = models.CharField(max_length=255)

    def __str__(self):
        return self.keyword


class Report(models.Model):
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    title = models.TextField()  # Changed from CharField
    date = models.DateField(null=True, blank=True)
    authors = models.TextField()  # Changed from CharField
    doc_type = models.CharField(max_length=100)
    subject = models.TextField()  # Changed from CharField
    description = models.TextField()
    report_file = models.FileField(upload_to='reports/', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title[:100]


class Activity(models.Model):
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()

    def __str__(self):
        return f"{self.activity_type}: {self.title}"
    

# Add this to your models.py

class Publication(models.Model):
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE, related_name='publications')
    title = models.CharField(max_length=500)
    authors = models.TextField(help_text="Comma-separated list of authors")
    journal = models.CharField(max_length=255, help_text="Journal or Conference name")
    publication_date = models.DateField()
    doi = models.CharField(max_length=100, blank=True, null=True, help_text="Digital Object Identifier")
    url = models.URLField(blank=True, null=True)
    abstract = models.TextField(blank=True, null=True)
    publication_type = models.CharField(
        max_length=50,
        choices=[
            ('journal', 'Journal Article'),
            ('conference', 'Conference Paper'),
            ('book', 'Book'),
            ('chapter', 'Book Chapter'),
            ('other', 'Other')
        ],
        default='journal'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-publication_date']

    def __str__(self):
        return self.title
