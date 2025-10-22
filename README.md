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
   source venv/Scripts/activate      # Git Bash
  
3. **Install Dependencies**
   
   ```bash
   pip install django
   pip install -r requirements.txt

4. **Run Migrations**
   
   ```bash
   python manage.py makemigrations
   python manage.py migrate


5. **Start Server**
    
   ```bash
   python manage.py runserver
   ```
   open http://127.0.0.1:8000/ in your browser.


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

;)
