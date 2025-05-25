<h1 align="center">Enterprise Payroll & HR Management System</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python" />
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
</p>

> A comprehensive, full-stack Enterprise Payroll and Human Resources Management architecture. Built to handle complex organizational structures, dynamic salary processing algorithms, and secure Role-Based Access Control (RBAC) over remote cloud databases.

## 🔥 Key Technical Implementations

* **Scalable Django Backend Architecture:** Engineered a rigorous MVC architecture utilizing Django, heavily optimizing the ORM layer to execute bulk transactional queries across the PostgreSQL worker databases.
* **Serverless Cloud Database Integration:** Connected and validated data models using Neon PostgreSQL, handling dynamic schema migrations without downtime.
* **Complex Data Engines:** Designed algorithmic processing systems capable of aggregating real-time attendance tracking, leave deductions, and dynamic tax brackets securely.
* **Testing & CI/CD Pipelines:** Implemented a rigorous `pytest` suite ensuring 90%+ code coverage on the core mathematical payroll algorithms to prevent production-level financial regressions.
* **Security & Roles:** Constructed strict Role-Based Access Control (RBAC) protocols, ensuring separation of concerns between standard Employees, HR Managers, and Root Administrators.

---

## 🏗️ Repository Architecture

```text
📦 Enterprise-Payroll-System-Django
 ┣ 📂 se_proj                               # Core Django Application & Settings
 ┣ 📂 myapp                                 # MVC Modules (Models, Views, Controllers)
 ┃ ┣ 📂 migrations                          # Database state tracking
 ┃ ┣ 📂 templates                           # Dynamic HTML/React Frontend Views
 ┃ ┣ 📂 static                              # CSS, JS, and Asset Pipelines
 ┃ ┣ 📜 models.py                           # PostgreSQL Schema Definitions
 ┃ ┣ 📜 views.py                            # Payroll Engine Logic
 ┃ ┗ 📜 tests.py                            # Pytest Coverage Suite
 ┣ 📂 media                                 # User-uploaded assets (Avatars, Documents)
 ┣ 📜 manage.py                             # Django CLI Engine
 ┣ 📜 requirements.txt                      # Immutable Dependency Graph
 ┣ 📜 pytest.ini                            # Test configuration
 ┣ 📜 .gitignore
 ┗ 📜 README.md
```

## 🚀 Quick Start (Local Deployment)

To deploy the Enterprise Payroll System locally using standard SQLite fallback or your configured PostgreSQL instance:

1. **Environment Initialization:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Execute Database Migrations:**
   ```bash
   python manage.py migrate
   ```
3. **Launch the Server Instance:**
   ```bash
   python manage.py runserver
   ```
*(Access the HR Manager dashboard at `http://localhost:8000/`)*

---
*Created by [Muhammad Mahad Khan](https://github.com/Mahad811)*
