from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models import Q

USER_TYPES = [
    ('admin', 'Admin'),
    ('researcher', 'Researcher'),
    ('student', 'Student'),
]

class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class ActiveManager(models.Manager):
    """Still used by Funding, Activity, Publication — keep it."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class CustomUser(AbstractUser):

    approval_status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending',  'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('inactive', 'Inactive'),
        ]
    )

    username         = models.CharField(max_length=150, unique=False, null=True, blank=True)
    email            = models.EmailField(_('email address'), unique=True)
    user_type        = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    supervisor       = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='students')
    organization     = models.CharField(max_length=100, blank=True, null=True)
    consent_to_share = models.BooleanField(default=False)
    force_password_change = models.BooleanField(default=False)
    temp_password_expires_at = models.DateTimeField(null=True, blank=True)

    totp_setup_started_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.user_type})"

    def save(self, *args, **kwargs):
        if self.user_type == 'researcher' and self.approval_status == 'approved':
            self.is_staff = True
        elif self.user_type == 'admin' or self.is_superuser:
            self.is_staff = True  # never touch admin/superuser
        else:
            self.is_staff = False
        super().save(*args, **kwargs)


class ResearcherProfile(models.Model):
    user              = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ccv_identifier    = models.CharField(max_length=255, blank=True, null=True)
    title             = models.CharField(max_length=100, blank=True, null=True)
    sex               = models.CharField(max_length=20, blank=True, null=True)
    language          = models.CharField(max_length=50, blank=True, null=True)
    residency_status  = models.CharField(max_length=100, blank=True, null=True)
    research_interests = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} Profile"


class Education(models.Model):
    external_id = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    researcher     = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    degree_type    = models.CharField(max_length=100, blank=True, null=True)
    specialization = models.CharField(max_length=255, blank=True, null=True)
    institution    = models.CharField(max_length=255, blank=True, null=True)
    thesis_title   = models.TextField(blank=True, null=True)
    start_date     = models.DateField(null=True, blank=True)      
    expected_date  = models.DateField(null=True, blank=True)     

    class Meta:
        unique_together = ("researcher", "external_id")

    def __str__(self):
        return f"{self.degree_type or 'Unknown'} at {self.institution or 'N/A'}"


class Recognition(models.Model):
    external_id = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    researcher       = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    name             = models.CharField(max_length=255)
    organization     = models.CharField(max_length=255, blank=True, null=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    recognition_type = models.CharField(max_length=100, blank=True, null=True)
    start_date       = models.DateField(null=True, blank=True)    # was CharField
    end_date         = models.DateField(null=True, blank=True)    # was CharField
    description      = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("researcher", "external_id")

    def __str__(self):
        return f"{self.name} ({self.organization})"


class Funding(SoftDeleteMixin, models.Model):
    objects     = ActiveManager()
    all_objects = models.Manager()
    external_id  = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    researcher   = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    funding_type = models.CharField(max_length=100, blank=True, null=True)
    title        = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True, null=True)
    amount       = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    start_date   = models.DateField(blank=True, null=True)
    end_date     = models.DateField(blank=True, null=True)
    program_name = models.CharField(max_length=500, blank=True, null=True,
                                    help_text="Funding program name from CCV")
    
    grant_total = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        help_text="Full project Total Funding from CCV, regardless of researcher's portion"
    )

    amount_to_ibme = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Portion of funding received by this researcher/institution"
    )

    currency = models.CharField(
        max_length=10,
        default='CAD',
        blank=True,
        choices=[('CAD', 'CAD'), ('USD', 'USD')],
    )
    

    project = models.ForeignKey(
        'Project',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='funding_breakdown',
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('submitted', 'Submitted'),
            ('awarded',   'Awarded'),
            ('rejected',  'Rejected'),
        ],
        blank=True, null=True,
        help_text="Outcome of this grant application"
    )

    role = models.CharField(
        max_length=20,
        choices=[
            ('pi',     'Principal Investigator'),
            ('co_pi',  'Co-Investigator'),
            ('pa',     'Principal Applicant'),
            ('co_app', 'Co-applicant'),
            ('other',  'Other'),
        ],
        blank=True, null=True,
        help_text="Researcher's role on this grant"
    )

    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status']),                  
        ]
        unique_together = ("researcher", "external_id")

    def __str__(self):
        return self.title


class StrategicObjective(models.Model):
    name  = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    DEFAULT_OBJECTIVES = [
        "Equity, Diversity & Inclusion",
        "Community Engagement",
        "Research Excellence",
        "Student Training & Mentorship",
        "Industry Partnership",
    ]

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def seed_strategic_objectives(sender, **kwargs):
    if sender.name != 'config':
        return
    # delete any that aren't in the list
    StrategicObjective.objects.exclude(
        name__in=StrategicObjective.DEFAULT_OBJECTIVES
    ).delete()
    # create any that are missing
    for i, name in enumerate(StrategicObjective.DEFAULT_OBJECTIVES):
        StrategicObjective.objects.get_or_create(name=name, defaults={'order': i})


class Activity(SoftDeleteMixin, models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ('presentation',  'Presentation'),
        ('broadcast',     'Broadcast Interview'),
        ('text_interview','Text Interview'),
    ]
    SOURCE_CHOICES = [
        ('ccv',    'CCV Import'),
        ('manual', 'Manually Logged'),
    ]
    CATEGORY_CHOICES = [
        ('conference',             'Conference'),
        ('knowledge_mobilization', 'Knowledge Mobilization'),
        ('media',                  'Media'),
        ('academic',               'Academic'),
        ('other',                  'Other'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)

    objects     = ActiveManager()
    all_objects = models.Manager()

    researcher    = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPE_CHOICES,
                                     default='presentation')
    title         = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    invited  = models.BooleanField(null=True, blank=True)
    keynote  = models.BooleanField(null=True, blank=True)
    description   = models.TextField(blank=True, null=True)
    date          = models.DateField(blank=True, null=True)
    external_id   = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    is_active     = models.BooleanField(default=True)
    projects      = models.ManyToManyField('Project', blank=True, related_name='linked_activities')
    source        = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='ccv')
    co_presenters = models.CharField(max_length=500, blank=True, null=True)
    audience      = models.CharField(max_length=255, blank=True, null=True)
    objectives = models.ManyToManyField(
        'StrategicObjective',
        blank=True,
        related_name='activities'
    )

    tagged_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='tagged_activities'
    )

    conference = models.ForeignKey(
        'Conference', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activities'
    )

    def soft_delete(self, user=None):
        self.is_active = False
        super().soft_delete(user=user) 

    class Meta:
        unique_together = ("researcher", "external_id")

    def __str__(self):
        return self.title


class ActivityReview(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    activity    = models.OneToOneField('Activity', on_delete=models.CASCADE,
                                       related_name='review')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='reviewed_activities')
    reason      = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.activity.title} — {self.status}"


class StudentNotification(models.Model):
    user       = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                   related_name='notifications')
    message    = models.TextField()
    request_id = models.IntegerField(null=True, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class SupervisorRequest(models.Model):

    student = models.ForeignKey("StudentProfile", on_delete=models.CASCADE)
    supervisor = models.ForeignKey("ResearcherProfile", on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending","Pending"),
            ("approved","Approved"),
            ("rejected","Rejected")
        ],
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "supervisor")

class Publication(SoftDeleteMixin, models.Model):
    objects     = ActiveManager()
    all_objects = models.Manager()
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE,
                                   related_name='publications')
    title      = models.CharField(max_length=500)
    authors    = models.TextField(help_text="Comma-separated list of authors")
    journal    = models.CharField(max_length=255, blank=True, null=True,
                                  help_text="Journal or Conference name")
    publication_date = models.DateField()
    doi              = models.CharField(max_length=100, blank=True, null=True)
    url              = models.URLField(blank=True, null=True)
    abstract         = models.TextField(blank=True, null=True)
    language         = models.CharField(max_length=100, blank=True, null=True)

    publication_type = models.CharField(
        max_length=50,
        choices=[
            ('journal',    'Journal Article'),
            ('conference', 'Conference Paper'),
            ('chapter',    'Book Chapter'),
            ('report',     'Research Report'),
            ('patent',     'Patent'),
            ('other',      'Other'),
        ],
        default='journal',
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('published',          'Published'),
            ('revision_requested', 'Revision Requested'),
            ('rejected',           'Rejected'),
            ('accepted',           'Accepted'),
            ('under_review',       'Under Review'),
            ('pending',            'Pending'),
            ('granted',            'Granted'),
            ('draft',              'Draft'),
        ],
        null=True, blank=True, default='published',
    )

    pages        = models.CharField(max_length=50, blank=True, null=True)
    refereed     = models.BooleanField(null=True, blank=True)
    volume       = models.CharField(max_length=50, blank=True, null=True)
    issue        = models.CharField(max_length=50, blank=True, null=True)
    publisher    = models.CharField(max_length=255, blank=True, null=True)
    open_access  = models.BooleanField(null=True, blank=True)

    conference_location  = models.CharField(max_length=255, blank=True, null=True)
    invited              = models.BooleanField(null=True, blank=True)
    book_title           = models.CharField(max_length=500, blank=True, null=True)
    editors              = models.CharField(max_length=255, blank=True, null=True)
    contribution_role    = models.CharField(max_length=100, blank=True, null=True)
    publication_location = models.CharField(max_length=100, blank=True, null=True)

    patent_number = models.CharField(max_length=100, blank=True, null=True)
    country       = models.CharField(max_length=100, blank=True, null=True)
    filing_date   = models.DateField(blank=True, null=True)

    external_id = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    is_active   = models.BooleanField(default=True)
    source      = models.CharField(
        max_length=20,
        choices=[('ccv', 'CCV Import'), ('manual', 'Manually Logged')],
        default='ccv',
    )
    projects = models.ManyToManyField('Project', blank=True, related_name='linked_publications')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-publication_date']
        indexes = [
            models.Index(fields=['publication_date']), 
        ]
        unique_together = ("researcher", "external_id")  

    
    def soft_delete(self, user=None):
        self.is_active = False
        super().soft_delete(user=user)

    def __str__(self):
        return self.title
        


class PublicationAuthor(models.Model):
    publication = models.ForeignKey('Publication', on_delete=models.CASCADE, 
                                    related_name='student_authors')
    student     = models.ForeignKey('StudentProfile', on_delete=models.CASCADE,
                                    related_name='publications')

    class Meta:
        unique_together = ('publication', 'student')


class ProjectQuerySet(models.QuerySet):
    def active(self):
        from datetime import date
        return self.filter(
            is_deleted=False,
            ccv_active=True,
            status__in=['awarded', 'pending', 'submitted'],
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=date.today())
        )

class ProjectManager(models.Manager):
    def get_queryset(self):
        return ProjectQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def active(self):
        return self.get_queryset().active()

class Project(SoftDeleteMixin, models.Model):
    STATUS_CHOICES = [
        ('awarded',   'Awarded'),
        ('completed', 'Completed'),
        ('pending',   'Pending'),
        ('submitted', 'Submitted'),
        ('rejected',  'Rejected'),
    ]
    ROLE_CHOICES = [
        ('pi',     'Principal Investigator'),
        ('co_pi',  'Co-Investigator'),
        ('pa',     'Principal Applicant'),
        ('co_app', 'Co-applicant'),
        ('other',  'Team Member'),
    ]
    
    objects     = ProjectManager()
    all_objects = models.Manager()
    
    external_id     = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    source          = models.CharField(max_length=20, choices=[('ccv', 'CCV Import'), ('manual', 'Manually Logged')], default='ccv')
    ccv_active = models.BooleanField(default=True)


    researcher          = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE,
                                            related_name='projects')
    title               = models.CharField(max_length=500)
    description         = models.TextField(blank=True, null=True)
    next_steps          = models.TextField(blank=True, null=True)
    conception          = models.TextField(blank=True, null=True,
                                           help_text="How the project idea originated")
    ip_activities       = models.TextField(blank=True, null=True)

    program_name = models.CharField(max_length=255, blank=True, null=True)

    # ── Dates — proper DateField now ──────────────────────────
    start_date          = models.DateField(blank=True, null=True)   # was CharField
    end_date            = models.DateField(blank=True, null=True)   # was CharField

    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='awarded')
    role                = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)

    funding_type        = models.CharField(max_length=100, blank=True, null=True)
    funding_organization = models.CharField(max_length=255, blank=True, null=True)
    total_funding       = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    funding_received    = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    funding_kept_by_unb = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        help_text="Amount of funding retained by UNB after overhead/indirect costs"
    )

    currency = models.CharField(
        max_length=10,
        default='CAD',
        blank=True,
        choices=[('CAD', 'CAD'), ('USD', 'USD')],
    )

    manually_overridden = models.BooleanField(
        default=False,
        help_text="If True, CCV re-uploads will not overwrite funding fields or status/role"
    )

    tagged_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='tagged_projects',
        help_text="RIMS users tagged as HQP or collaborators on this project"
    )

    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['start_date', 'end_date']), 
        ]
        unique_together = ("researcher", "external_id")

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        from datetime import date
        if self.status in ('completed', 'rejected'):
            return False
        if self.end_date is None:
            return True
        return self.end_date >= date.today()


class ProjectMember(models.Model):
    ROLE_CHOICES = [
        ('pi',     'Principal Investigator'),
        ('co_pi',  'Co-Investigator'),
        ('pa',     'Principal Applicant'),
        ('co_app', 'Co-applicant'),
        ('other',  'Team Member'),
    ]
    DEGREE_CHOICES = [
        ('undergrad', 'Undergraduate'),
        ('msc',       'MSc'),
        ('phd',       'PhD'),
        ('pdf',       'Post-Doctoral Fellow'),
        ('ra',        'Research Associate'),
        ('other',     'Other'),
    ]
    PARTNER_TYPE_CHOICES = [
        ('academic',   'Academic'),
        ('industry',   'Industry'),
        ('community',  'Community'),
        ('government', 'Government'),
        ('other',      'Other'),
    ]

    project      = models.ForeignKey(Project, on_delete=models.CASCADE,
                                     related_name='team_members')
    name         = models.CharField(max_length=255)
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='other')
    degree_level = models.CharField(max_length=20, choices=DEGREE_CHOICES,
                                    blank=True, null=True)
    department   = models.CharField(max_length=255, blank=True, null=True)
    partner_type = models.CharField(
        max_length=20, choices=PARTNER_TYPE_CHOICES,
        blank=True, null=True,
        help_text="Type of collaborator or partner"
    )
    is_academic_collaborator = models.BooleanField(
        default=False,
        help_text="Legacy — use partner_type instead"
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.get_role_display()}"

class StudentProfile(models.Model):
    DEGREE_CHOICES = [
        ('undergrad', 'Undergraduate'),
        ('msc',       'MSc'),
        ('phd',       'PhD'),
        ('pdf',       'Post-Doctoral Fellow'),
        ('ra',        'Research Associate'),
        ('other',     'Other'),
    ]

    GENDER_CHOICES = [
        ('female', 'Female'),
        ('male', 'Male'),
        ('non_binary', 'Non-binary'),
        ('prefer_not', 'Prefer not to say'),
        ('self_describe', 'Prefer to self-describe'),
    ]

    RESIDENCY_CHOICES = [
        ('citizen', 'Canadian Citizen'),
        ('permanent_resident', 'Permanent Resident'),
        ('international', 'International Student'),
        ('prefer_not', 'Prefer not to say'),
    ]

    INDIGENOUS_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('prefer_not', 'Prefer not to say'),
    ]

    RACE_ETHNICITY_CHOICES = [
        ('white',          'White / European descent'),
        ('black',          'Black / African descent'),
        ('east_asian',     'East Asian'),
        ('south_asian',    'South Asian'),
        ('southeast_asian','Southeast Asian'),
        ('latin',          'Latin American / Hispanic'),
        ('middle_eastern', 'Middle Eastern / North African'),
        ('indigenous',     'Indigenous (other than First Nations/Métis/Inuit)'),
        ('mixed',          'Two or more ethnicities'),
        ('other',          'Other'),
        ('prefer_not',     'Prefer not to say'),
    ]

    race_ethnicity = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=RACE_ETHNICITY_CHOICES,
        verbose_name='Race / Ethnicity',
    )

    user              = models.OneToOneField(CustomUser, on_delete=models.CASCADE,
                                             related_name='student_profile')
    degree_level      = models.CharField(max_length=20, choices=DEGREE_CHOICES,
                                         blank=True, null=True)
    department        = models.CharField(max_length=255, blank=True, null=True)
    supervisor = models.ForeignKey(
        ResearcherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students"
    )
    co_supervisors = models.ManyToManyField(    
        ResearcherProfile,
        blank=True,
        related_name="co_supervised_students",
    )
    start_date        = models.DateField(blank=True, null=True)
    expected_end_date = models.DateField(blank=True, null=True)
    thesis_title      = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    graduation_date = models.DateField(blank=True, null=True)

    gender               = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    indigenous_identity  = models.CharField(max_length=20, choices=INDIGENOUS_CHOICES, blank=True, null=True)
    residency_status     = models.CharField(max_length=20, choices=RESIDENCY_CHOICES, blank=True, null=True)
    edi_profile_completed = models.BooleanField(default=False)

    manually_overridden = models.BooleanField(
        default=False,
        help_text="If True, CCV re-uploads will not overwrite manually edited fields"
    )

    class Meta:
        indexes = [
            models.Index(fields=['graduation_date']),        
            models.Index(fields=['start_date']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_degree_level_display()})"

    @property
    def degree_label(self):
        mapping = {
            'undergrad': 'Undergraduate',
            'msc': 'MSc',
            'phd': 'PhD',
            'pdf': 'Post-Doctoral Fellow',
            'ra': 'Research Associate',
            'other': 'Other',
        }
        return mapping.get(self.degree_level, self.degree_level or '')

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('user_registered',       'User Registered'),
        ('user_approved',         'User Approved'),
        ('user_rejected',         'User Rejected'),
        ('user_login',    'User Login'),
        ('login_failed',  'Login Failed'),
        ('login_pending', 'Login Attempt — Pending Account'),
        ('ccv_uploaded',          'CCV Uploaded'),
        ('ccv_student_uploaded',  'Student CCV Uploaded'),
        ('activity_submitted',    'Activity Submitted'),
        ('activity_approved',     'Activity Approved'),
        ('activity_rejected',     'Activity Rejected'),
        ('activity_deleted',      'Activity Deleted'),
        ('supervisor_requested',  'Supervisor Requested'),
        ('supervisor_approved',   'Supervisor Approved'),
        ('supervisor_rejected',   'Supervisor Rejected'),
        ('publication_added',     'Publication Added'),
        ('publication_updated',   'Publication Updated'),
        ('publication_deleted',   'Publication Deleted'),
        ('project_created',       'Project Created'),
        ('project_updated',       'Project Updated'),
        ('project_deleted',       'Project Deleted'),
        ('hqp_tagged',            'HQP Tagged'),
        ('hqp_untagged',          'HQP Untagged'),
        ('profile_updated',       'Profile Updated'),
        ('edi_updated',           'EDI Profile Updated'),
        ('consent_updated',       'Consent Updated'),
        ('report_uploaded',       'Report Uploaded'),
        ('report_deleted',        'Report Deleted'),
        ('other',                 'Other'),
        ('user_created_by_admin',   'User Created by Admin'),
        ('password_changed',        'Password Changed'),
        ('password_reset_by_admin', 'Password Reset by Admin'),
        ('user_deactivated', 'User Deactivated'),
        ('user_deleted',     'User Deleted'),
    ]

    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs',
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_type  = models.CharField(max_length=50, blank=True, null=True)
    target_id    = models.PositiveIntegerField(null=True, blank=True)
    summary      = models.CharField(max_length=500, blank=True, null=True)
    details      = models.JSONField(default=dict, blank=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        who = self.user.get_full_name() if self.user else 'System'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {who} — {self.get_action_display()}"

class Conference(models.Model):
    name     = models.CharField(max_length=255)
    acronym  = models.CharField(max_length=50, blank=True, null=True)
    year     = models.IntegerField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-year', 'name']
        unique_together = ('name', 'year')

    def __str__(self):
        return f"{self.acronym or self.name} {self.year or ''}".strip()

class SupervisionRecord(models.Model):
    DEGREE_CHOICES = [
        ('bachelors', "Bachelor's"),
        ('masters_thesis', "Master's Thesis"),
        ('masters_non_thesis', "Master's Non-Thesis"),
        ('doctorate', 'Doctorate'),
        ('postdoc', 'Post-doctorate'),
        ('research_associate', 'Research Associate'),
    ]

    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    external_id       = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    researcher        = models.ForeignKey(
        ResearcherProfile,
        on_delete=models.CASCADE,
        related_name='supervision_records'
    )

    student_name      = models.CharField(max_length=255)
    institution       = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    degree_type       = models.CharField(max_length=30, choices=DEGREE_CHOICES, blank=True, null=True)
    supervision_role  = models.CharField(max_length=50, blank=True, null=True)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)

    start_date        = models.DateField(blank=True, null=True)
    end_date          = models.DateField(blank=True, null=True)
    degree_start_date = models.DateField(blank=True, null=True)
    degree_end_date   = models.DateField(blank=True, null=True)
    expected_date     = models.DateField(blank=True, null=True)

    thesis_title      = models.TextField(blank=True, null=True)
    present_position  = models.CharField(max_length=500, blank=True, null=True)
    present_org       = models.CharField(max_length=500, blank=True, null=True)
    residency_status  = models.CharField(max_length=100, blank=True, null=True)

    department = models.CharField(max_length=255, blank=True, null=True)

    manually_overridden = models.BooleanField(
        default=False,
        help_text="If True, CCV re-uploads will not overwrite manually edited fields"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    linked_student = models.ForeignKey(
        'StudentProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='supervision_records',
        help_text="Linked RIMS student account if registered"
    )

    class Meta:
        unique_together = ('researcher', 'external_id')
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['degree_type']),
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
        ]

    def __str__(self):
        degree = self.get_degree_type_display() if self.degree_type else "Unknown"
        supervisor = self.researcher.user.get_full_name() if self.researcher else "Unknown"
        return f"{self.student_name} — {degree} under {supervisor}"