# ENGG4000_RIMS_MGMT
Research Information Management System (RIMS) developed as part of ENGG4000. A full-stack web application for managing research data including publications, grants, student activities, and reporting. 

Built with Django (backend) and HTML/CSS/JS (frontend), featuring secure authentication, role-based access, dynamic forms, and reporting tools.

## How to Run

1. **Clone the Repository**
   
   ```bash
   git clone https://github.com/athuduku/ENGG4000_RIMS_MGMT.git
   cd ENGG4000_RIMS_MGMT/backend

2. **Create and Activate Virtual Environment**
   
   ```bash
   python -m venv venv
   source venv/Scripts/activate  
  
3. **Install Dependencies**
   
   ```bash
   pip install django
   pip install -r requirements.txt

4. **Setup Database**

   Create a file named .env under the backend folder and fill out based on your PostgreSQL database info:

   ```bash
   DB_NAME=(DB_NAME)
   DB_USER=postgres
   DB_PASSWORD=(DB_PASSWORD)
   DB_HOST=localhost
   DB_PORT=5432

6. **Run Migrations**
   
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   
7. **Start Server**
    
   ```bash
   python manage.py runserver
   ```
   Then open your browser and visit:
   http://127.0.0.1:8000/

9. To create a superuser for admin access:

   ```bash
   python manage.py createsuperuser
   ```
   Then log in at http://127.0.0.1:8000/admin/


## How to Push

1. **Pull the latest changes from GitHub**
   ```bash
   git pull origin main
   ```

2. **Add files and comment**
   ```bash
   git status
   git add .
   git commit -m "COMMENTS"

3. **Push your changes**
   ```bash
   git push origin main

## How to Create a Pull Request (PR)

1. **Create a New Branch**
Before making any changes, create a feature branch:
   ```bash
   git checkout -b feature/feature-name
   ```

2. **Make Your Changes**

   Update code, test features locally, and verify everything still works.

3. **Stage and Commit**
   ```bash
   git add .
   git commit -m "Describe the feature"
   ```
4. **Push Your Branch**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request on GitHub**

   1. Go to your repository on GitHub
   
   2. You will see a “Compare & pull request” button
   
   3. Set:
      - Base branch: `main`
      - Compare branch: your feature branch
      - Add a clear title and description

   4. Submit the PR

## How to Review a Pull Request

1. Go to the Pull Requests tab on GitHub

2. Select the PR you want to review

3. Review changed files using the Files changed tab

4. Add comments, requests for changes, or approval

5. If changes are needed:
   - Updates the branch
   - Pushes again
   - PR updates automatically

Once approved and confirmed working, merge the pull request into `main`.

## Recommended Branch Workflow:
| Branch | Purpose |
|---|---|
| `main` | Production code |
| `feature/*` | New features |
| `fix/*` | Bug fixes |
| `test/*` | Experimental or testing updates |
