# RIMS | Research Information Management System

A Django 5.2 + PostgreSQL web application built for the UNB Institute of Biomedical Engineering (IBME). RIMS centralises researcher profiles, CCV XML bulk imports, project/publication/activity tracking, supervision records, and director-level reporting for ~50 users across three roles: Admin, Researcher, and Student.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Running Tests](#running-tests)
- [CI/CD](#cicd)
- [Key Features](#key-features)
- [User Roles](#user-roles)

---

## Project Structure

```
ENGG4000_RIMS_MGMT/
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI pipeline
├── backend/
│   ├── .env                        # Environment variables (not committed)
│   ├── manage.py
│   ├── requirements.txt
│   ├── scripts/
│   │   └── debug_xml.py/           # Dev utility (not used in production)             
│   ├── config/                     # Main Django application
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── middleware.py
│   │   ├── models.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── utils.py
│   │   ├── views.py
│   │   ├── wsgi.py / asgi.py
│   │   ├── migrations/             # Database migrations (0001 – 0039)
│   │   ├── templatetags/
│   │   │   └── auth_extras.py
│   │   └── tests/
│   │       ├── test_auth.py
│   │       ├── test_bulkupload.py
│   │       ├── test_db_con.py
│   │       ├── test_funding.py
│   │       ├── test_models.py
│   │       ├── test_permissions.py
│   │       └── test_upload_and_api.py
│   └── venv/                       # Virtual environment (not committed)
├── frontend/
│   ├── admin/
│   │   └── base_site.html          # Custom Django admin branding
│   ├── emails/
│   │   ├── password_reset_email.html
│   │   └── password_reset_subject.txt
│   ├── Pages/                      # All HTML templates
│   │   ├── dashboard.html
│   │   ├── home.html
│   │   ├── notifications.html
│   │   ├── profile_modal.html
│   │   ├── sidebar.html
│   │   ├── student_dashboard.html
│   │   ├── editable/
│   │   │   └── profile.html
│   │   ├── forms/
│   │   │   ├── activity_detail_modal.html
│   │   │   ├── add_publication.html
│   │   │   ├── bulk_upload_ccv.html
│   │   │   ├── linked_publications.html
│   │   │   ├── log_activity.html
│   │   │   ├── upload_research_report.html
│   │   │   ├── view_activities.html
│   │   │   └── view_publications.html
│   │   ├── projects/
│   │   │   ├── add_project.html
│   │   │   ├── project_detail_modal.html
│   │   │   └── view_projects.html
│   │   ├── reports/
│   │   │   ├── active_projects_report.html
│   │   │   ├── activity_report.html
│   │   │   ├── conference_equity_report.html
│   │   │   ├── conference_equity_summary.html
│   │   │   ├── enrollment_trends_report.html
│   │   │   ├── funding_analysis_report.html
│   │   │   ├── grad_completion_report.html
│   │   │   ├── pi_report.html
│   │   │   └── reports_list.html
│   │   └── User_Auth/
│   │       ├── login.html
│   │       ├── login_2fa.html
│   │       ├── ratelimited.html
│   │       ├── reset_confirm.html
│   │       ├── reset_done.html
│   │       ├── setup_2fa.html
│   │       ├── set_password.html
│   │       └── signup.html
│   └── static/
│       ├── assets/                 # Images and logos
│       ├── css/                    # Per-page stylesheets
│       └── js/                     # Per-page JavaScript
└── README.md
```

---

## Prerequisites

- Python 3.12
- PostgreSQL 14+
- Git

---

## Environment Setup

Create a `.env` file inside the `backend/` directory (next to `manage.py`). **Never commit this file.**

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DB_NAME=rims_db
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

ALLOWED_HOSTS=localhost,127.0.0.1
```

### Generating a SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/athuduke/ENGG4000_RIMS_MGMT.git
cd ENGG4000_RIMS_MGMT

# 2. Create and activate a virtual environment
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the .env file (see Environment Setup above)

# 5. Create the PostgreSQL database
psql -U postgres -c "CREATE DATABASE rims_db;"

# 6. Run migrations
python manage.py migrate

# 7. Create a superuser (Admin)
python manage.py createsuperuser

# 8. Collect static files (production)
python manage.py collectstatic
```

---

## Running the App

```bash
cd backend
python manage.py runserver
```
Environment Setup
The app will be available at `http://127.0.0.1:8000`.

The Django admin panel is at `http://127.0.0.1:8000/admin-portal`.

---

## Running Tests

All 30 tests should pass with the default configuration.

```bash
cd backend
python manage.py test config.tests
```

To run a specific test module:

```bash
python manage.py test config.tests.test_auth
```

> **Note:** Set `RATELIMIT_ENABLE=False` in your `.env` (or ensure `DEBUG=True`) before running tests, otherwise rate-limit-protected views will block test requests.

---

## CI/CD

GitHub Actions runs automatically on every push and pull request to `main`. The pipeline:

1. Spins up a PostgreSQL 14 service container
2. Installs Python 3.12 and project dependencies
3. Runs all Django tests via `manage.py test`

Required GitHub repository secrets:

| Secret | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DB_NAME` | Database name (e.g. `rims_db`) |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | Matches `DB_NAME` for the service container |
| `POSTGRES_USER` | Matches `DB_USER` for the service container |
| `POSTGRES_PASSWORD` | Matches `DB_PASSWORD` for the service container |

The Cypress E2E workflow (`.github/workflows/cypress.yml`) is currently set to `workflow_dispatch` only and requires additional setup before enabling.

---

## Key Features

- **CCV XML Bulk Import** - Researchers and admins can upload CCV XML files to auto-populate projects, publications, activities, funding records, and education. Manual records are preserved and optionally claimed by CCV data on re-upload.
- **Two-Factor Authentication (2FA)** - Mandatory TOTP-based 2FA for all roles using `django-two-factor-auth`. Backup codes and admin reset available.
- **Role-Based Access Control** - Three roles (Admin, Researcher, Student) with permission checks on every view.
- **Supervision Records** - Tracks supervisor/co-supervisor relationships, student academic profiles, and auto-linking via last name matching.
- **Audit Logging** - All significant actions (login, data changes, imports) are recorded with user, timestamp, and IP.
- **Soft Delete** - Core models use `SoftDeleteMixin`; deleted records are hidden but recoverable.
- **Reports (7 Director-Level)** - Active projects, PI summary, enrollment trends, funding analysis, grad completion, activity breakdown, and conference equity (with CSV export).
- **Notifications** - Tabbed notification centre with real-time polling.
- **Rate Limiting & Brute-Force Protection** - `django-ratelimit` on auth endpoints; `django-axes` for login attempt tracking.

---

## User Roles

| Role | Capabilities |
|---|---|
| **Admin** | Full access: user management, temp password issuance, all reports, audit logs, Django admin |
| **Researcher** | CCV import, manage own projects/publications/activities, view supervised students, PI report |
| **Student** | View linked publications, log activities, edit academic profile, submit supervisor requests |

---

## Dependencies

Key packages (see `requirements.txt` for pinned versions):

- `Django==5.2.6`
- `psycopg2-binary==2.9.11`
- `django-two-factor-auth==1.18.1`
- `django-otp==1.7.0`
- `django-axes==8.3.1`
- `django-ratelimit==4.1.0`
- `defusedxml==0.7.1`
- `python-decouple==3.8`
- `openpyxl==3.1.5`
- `PyPDF2==3.0.1`
- `jsonschema==4.25.1`
- `qrcode==8.2`
- `Pillow==12.0.0`