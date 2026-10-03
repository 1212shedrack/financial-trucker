# Personal Financial Analytics and Management System (PFAMS)

A full-stack, secure, responsive, and offline-capable personal financial management system tailored for the Tanzanian market, featuring **Tanzanian Shillings (TZS)**, localized payment methods (M-Pesa, Airtel Money, Tigo Pesa), statistical analytics with **Pandas & NumPy**, and a progressive web app (**PWA**) with offline sync.

---

## 🌟 Key Features

- **📊 Comprehensive Financial Tracking:**
  - Income & Expense recording with categories, payment methods (Cash, M-Pesa, Airtel Money, Tigo Pesa, Bank, Card), dates, notes, and file/receipt attachments.
  - Multi-condition filtering, search, sorting, and pagination.
  - Combined chronological transaction feed.

- **🎯 Savings Goals & Budgets:**
  - Category-based monthly, weekly, and custom budgets with automated progress bars and threshold warnings (80% warning, >100% exceeded).
  - Target-oriented savings goals with contribution deposit tracking, milestone alerts (25%, 50%, 75%, 100%), and deadline countdowns.

- **🔄 Scheduled & Recurring Transactions:**
  - Daily, weekly, monthly, and yearly recurring schedules for salaries, rent, utility bills, subscriptions with automated due date advancement.

- **📈 Advanced Analytics (Pandas & NumPy):**
  - Cash flow summaries, savings rates, and burn rates.
  - 12-month inflow/outflow trends, category spending distribution, payment channel breakdowns, and income stream compositions.
  - **Z-Score Anomaly Detection:** Flags statistically unusual daily spending spikes (> 2 standard deviations).
  - Rule-based financial health insights (ML-ready service architecture).

- **📑 Reporting & Data Portability:**
  - Export customizable statements as **PDF** (ReportLab formatted report), **Excel** (`.xlsx` formatted with openpyxl), or **CSV** (UTF-8 with BOM).
  - Batch CSV import tool with dry-run preview, row-by-row validation, error reporting, and atomic database commits.

- **📶 Progressive Web App (PWA) & Offline Capability:**
  - Service Worker caching strategy for lightning-fast loads.
  - Client-side **IndexedDB** queue for offline transactions with automatic synchronization upon network reconnection (`/api/sync/`).
  - Web App Manifest supporting desktop and mobile installation.

- **🔒 Security & Localization:**
  - Complete user data isolation (strict `request.user` queryset filtering).
  - DecimalField-only monetary precision (no floating-point rounding errors).
  - Activity audit logging (`AuditLog`), password reset flows, secure sessions, and dark/light mode toggling.
  - Tanzanian Shillings format (`TSh 1,500,000`) and Dar es Salaam timezone (`Africa/Dar_es_Salaam`).

---

## 🛠️ Tech Stack & Architecture

- **Backend:** Django 5.0.6, Django REST Framework 3.15.2, Python 3.12
- **Data & Analytics:** Pandas 2.2.2, NumPy 1.26.4
- **Reports:** ReportLab 4.2.2, openpyxl 3.1.4
- **Frontend:** Bootstrap 5.3, Bootstrap Icons 1.11, Chart.js 4.4, Custom CSS/JS
- **Offline & Storage:** Service Worker API, IndexedDB API, Web App Manifest
- **Environment:** `python-decouple`, `whitenoise`

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Virtual Environment

### 2. Setup & Virtual Environment
```bash
# Clone or navigate to the directory
cd "C:\Users\SHEDRACK\OneDrive\Desktop\truker"

# Activate the virtual environment
.\venv\Scripts\activate

# Install dependencies (already pre-installed)
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env` if not already present:
```bash
cp .env.example .env
```

### 4. Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed Default Data & Demo User
```bash
# Create default categories and a pre-populated demo account
python manage.py seed_data --demo
```
**Demo Account Credentials:**
- **Email / Username:** `demo@pfams.com` / `demo`
- **Password:** `Demo1234!`

### 6. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Running the Test Suite

Execute the full suite of unit and integration tests:
```bash
python manage.py test tests
```

---

## 📁 Project Structure

```
truker/
├── personal_finance/       # Root project configuration (settings, urls, wsgi, asgi)
├── core/                   # Core views, landing, dashboard, audit log, DRF API router, sync
├── accounts/               # User registration, profile, authentication, security
├── transactions/           # Categories, Incomes, Expenses, Recurring Transactions
├── budgets/                # Category budget tracking, threshold warnings
├── goals/                  # Savings goals & contribution history
├── analytics/              # Pandas/NumPy analytics services, anomaly detection
├── notifications/          # In-app alerts, budget warnings, milestone triggers
├── reports/                # PDF, Excel, CSV exports and batch CSV importer
├── templates/              # Responsive Bootstrap 5 HTML templates
├── static/                 # Custom CSS, JS, IndexedDB offline sync, Service Worker, icons
├── media/                  # User receipts and attachments
├── tests/                  # Automated tests (models, views, analytics, api)
├── manage.py
├── requirements.txt
└── .env
```

---

## 📄 License
MIT License. Built for Tanzania & personal finance tracking.
