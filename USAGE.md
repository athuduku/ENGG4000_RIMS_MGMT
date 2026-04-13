# RIMS Usage Guide

This guide covers common tasks for each role in the system. RIMS has three roles: **Admin**, **Researcher**, and **Student**.

---

## Table of Contents

- [First-Time Login & 2FA Setup](#first-time-login--2fa-setup)
- [Password Reset](#password-reset)
- [Admin Tasks](#admin-tasks)
  - [Approving New User Accounts](#approving-new-user-accounts)
  - [Issuing a Temporary Password](#issuing-a-temporary-password)
  - [Resetting a User's 2FA](#resetting-a-users-2fa)
  - [Unlocking a Locked-Out User](#unlocking-a-locked-out-user)
  - [Viewing Audit Logs](#viewing-audit-logs)
  - [Running Reports](#running-reports)
- [Researcher Tasks](#researcher-tasks)
  - [CCV XML Bulk Upload](#ccv-xml-bulk-upload)
  - [Re-uploading a CCV File](#re-uploading-a-ccv-file)
  - [Adding a Project Manually](#adding-a-project-manually)
  - [Adding a Publication Manually](#adding-a-publication-manually)
  - [Logging an Activity](#logging-an-activity)
  - [Linking a Student](#linking-a-student)
  - [Viewing Your PI Report](#viewing-your-pi-report)
- [Student Tasks](#student-tasks)
  - [Submitting a Supervisor Request](#submitting-a-supervisor-request)
  - [Editing Your Academic Profile](#editing-your-academic-profile)
  - [Viewing Linked Publications](#viewing-linked-publications)
- [Common Issues](#common-issues)

---

## First-Time Login & 2FA Setup

2FA is **mandatory** for all users. Every new account must complete setup on first login.

1. Navigate to `http://127.0.0.1:8000` (or your deployed URL).
2. Enter your email and password on the login page.
3. You will be redirected to the **2FA Setup** page.
4. Open an authenticator app on your phone (e.g. Google Authenticator, Authy, Microsoft Authenticator).
5. Scan the QR code shown on screen.
6. Enter the 6-digit code from your app to confirm setup.
7. **Save your backup codes** - these are shown once and allow you to log in if you lose access to your authenticator app.

On subsequent logins, after entering your password you will be prompted for the 6-digit TOTP code from your authenticator app.

---

## Password Reset
 
Password resets are handled by the system admin. There is no self-serve email reset link.
 
If you have forgotten your password:
 
1. Contact your system admin directly and ask them to issue a temporary password.
2. The admin will generate a temporary password from the admin panel and share it with you securely (in person, over Teams, or by phone - never by email in plaintext).
3. Log in using the temporary password - you will be prompted to set a new password immediately.
4. After setting your new password, complete the 2FA step as usual.
 
> **Note:** Temporary passwords expire after a short period. Log in and change your password as soon as you receive it.

---

## Admin Tasks

Access the admin area by logging in and navigating to **`/admin-portal`**, or through the sidebar if you have admin role.

---

### Approving New User Accounts

New accounts require admin approval before they can log in.

1. Go to **Admin Portal → Users → Pending Approvals** (or via Django admin at `/admin-portal`).
2. You will see a list of users with `approval_status = pending`.
3. Click a user to open their profile.
4. Set their **Approval Status** to `approved` and save.
5. The user will receive a notification and can now log in.

> **Note:** There is a cap on pending accounts to prevent abuse. If the system rejects new signups, check the pending queue and clear old or invalid requests.

---

### Issuing a Temporary Password

Use this when a user cannot reset their own password (e.g. no email access).

1. In Django admin (`/admin-portal`), go to **Users** and find the account.
2. Click **Issue Temp Password** from the user detail page.
3. A modal will display a generated temporary password - copy it and share it securely with the user.
4. The temporary password expires after a set period. The user will be forced to set a new password on next login.

---

### Resetting a User's 2FA

If a user has lost access to their authenticator app and has no backup codes:

1. Go to Django admin (`/admin-portal`) → **Users** → find the user.
2. Click **Reset 2FA** (or clear their OTP device from the **OTP Devices** section).
3. The user can now log in with just their password and will be prompted to set up 2FA again from scratch.

---

### Unlocking a Locked-Out User

After too many failed login attempts, `django-axes` automatically locks the account.

1. Go to Django admin (`/admin-portal`) → **Axes** → **Access Attempts**.
2. Find the entry for the user (by username or IP address).
3. Select it and choose **Reset** (or delete the access attempt record).
4. The user can now attempt to log in again.

Alternatively, from the command line:
```bash
cd backend
python manage.py axes_reset_username <username>
```

---

### Viewing Audit Logs

All significant actions in RIMS are recorded automatically.

1. Go to Django admin (`/admin-portal`) → **Audit Logs**.
2. Filter by user, action type, or date range.
3. Each entry records: who performed the action, what was changed, the timestamp, and the IP address.

---

### Running Reports

Seven director-level reports are available under the **Reports** section of the sidebar.

| Report | Description |
|---|---|
| Active Projects | All currently active grants and projects across researchers |
| PI Summary | Publications, students, and funding per principal investigator |
| Enrollment Trends | Student enrollment over time by program/year |
| Funding Analysis | Funding received vs. total by organization and year |
| Grad Completion | Student graduation timelines and completion rates |
| Activity Breakdown | Conference presentations, workshops, and other activities |
| Conference Equity | Gender/EDI breakdown of conference participation (CSV export available) |

To export a report, open it and click the **Export CSV** button where available.

---

## Researcher Tasks

---

### CCV XML Bulk Upload

CCV (Common CV) is the standard academic CV format used by Canadian funding agencies. RIMS can parse a CCV XML export and automatically populate your profile.

**Getting your CCV XML file:**
1. Log in to your account at [ccv-cvc.ca](https://ccv-cvc.ca).
2. Go to **Export** and select **XML** format.
3. Download the file to your computer.

**Uploading to RIMS:**
1. Log in to RIMS and go to **Bulk Upload CCV** from the sidebar.
2. Click **Choose File** and select your downloaded CCV XML file.
3. Click **Upload**.
4. RIMS will parse and import the following sections:
   - Personal information & contact details
   - Education history
   - Projects (grants and research projects)
   - Funding records
   - Publications (journal articles, conference papers, books)
   - Activities (presentations, workshops, committees)
   - Recognition & awards
   - Student supervision records
5. A summary of imported records will be displayed after upload.

> **Tip:** If the upload fails, check that your file is a valid CCV XML export. RIMS validates against the CCV schema.

---

### Re-uploading a CCV File

You can re-upload a newer CCV file at any time. RIMS handles this intelligently:

- **CCV-sourced records** (previously imported) are updated with the latest data from your new file.
- **Manually added records** that have not been edited are matched to your CCV by title and claimed - they will be updated going forward.
- **Manually edited records** (`manually_overridden = True`) are **protected** - their key fields will not be overwritten by the CCV import. You remain in control of those records.
- Team members you added manually to projects are always preserved.

---

### Adding a Project Manually

1. Go to **Projects** in the sidebar.
2. Click **Add Project**.
3. Fill in the project details across the tabs:
   - **Tab 1:** Title, status, role, funding type, dates
   - **Tab 2:** Funding organization, amounts, currency
   - **Tab 3:** Team members, HQP tags
   - **Tab 4:** Description, conception, next steps
4. Click **Save**.

Manually added projects appear in all relevant reports. Note that they will not appear in the **Grants by Researcher** bar chart (which reads from CCV-sourced Funding records) until a matching CCV upload claims them.

---

### Adding a Publication Manually

1. Go to **Publications** in the sidebar.
2. Click **Add Publication**.
3. Enter the publication details (title, journal, authors, year, DOI, status).
4. Click **Save**.

Publications with a status of `published` or `in_press` are protected from being overwritten by CCV re-uploads.

---

### Logging an Activity

Activities include conference presentations, workshops, seminars, committee work, and other knowledge mobilisation events.

1. Go to **Activities** in the sidebar.
2. Click **Log Activity**.
3. Fill in the form:
   - **Title** and **date**
   - **Category** - RIMS will auto-suggest a category based on keywords in the title; you can override it
   - **Conference** - if applicable, link to an existing conference record
   - **Description** (optional)
4. Click **Save**.

---

### Linking a Student

Researchers can be linked to students they supervise. Linking happens automatically when a student signs up with a last name that matches a supervision record from your CCV. You can also link manually:

1. Go to **Django admin** → **Supervision Records**.
2. Find or create the supervision record for the student.
3. Set the **Linked Student** field to the student's user account.

Once linked, the student appears on your dashboard under **Students Supervising**, and their profile is accessible from your supervision records.

---

### Viewing Your PI Report

1. Go to **Reports** in the sidebar.
2. Click **PI Summary Report**.
3. The report shows your publications count, active students, funding received, and activity breakdown.
4. Use the date range filters to narrow the report period.

---

## Student Tasks

---

### Submitting a Supervisor Request

If you are not yet linked to a supervisor in RIMS, you can submit a request.

1. Log in and go to your **Dashboard**.
2. Click **Request Supervisor**.
3. Search for your supervisor by name.
4. Select the correct researcher and click **Submit Request**.
5. Your supervisor will be notified. Once they approve, you will be linked to their profile and your supervision record will be created.

---

### Editing Your Academic Profile

1. Click your name or avatar in the sidebar to open your **Profile**.
2. Click **Edit Profile**.
3. You can update:
   - Program and department
   - Start and expected end date
   - Degree level
   - EDI information (race/ethnicity - used only for anonymised equity reporting)
4. Click **Save**.

> **Note:** Once you edit your academic profile, it is marked as manually managed (`manually_overridden = True`). Your supervisor's CCV re-uploads will no longer overwrite these fields.

---

### Viewing Linked Publications

Publications that your supervisor has tagged with your name will appear in your **Linked Publications** list.

1. Go to **Publications** in the sidebar.
2. The **Linked Publications** tab shows all publications associated with your supervision record.
3. You can view full details but cannot edit supervisor-owned publications.

---

## Common Issues

| Issue | Solution |
|---|---|
| Can't log in after signing up | Your account is pending admin approval. Contact your system admin. |
| Lost authenticator app access | Use a backup code, or ask your admin to reset your 2FA. |
| CCV upload fails with a schema error | Ensure you exported the file as **XML** from the CCV portal (not PDF). |
| CCV upload succeeds but some records are missing | Check that those sections are populated in your CCV. Empty sections are skipped. |
| Activity category is wrong | You can manually override the category in the activity detail view. |
| Project is not appearing in the Grants chart | The chart only reads CCV-sourced funding records. Re-upload your CCV or add a Funding record manually via the admin panel. |
| Account locked after failed logins | Contact your admin to reset your access attempt record. |
| Temp password expired | Ask your admin to issue a new temporary password. |