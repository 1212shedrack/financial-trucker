
================================================================================
        PFAMS — PERSONAL FINANCIAL ANALYTICS & MANAGEMENT SYSTEM
                       README / DOCUMENTATION FILE
================================================================================

Project Name  : PFAMS — Personal Financial Analytics & Management System
Version       : 1.0.0
Author        : Musa (PFAMS Project Owner)
Framework     : Django 5.0.6 (Python 3.12)
Database      : SQLite (development) / PostgreSQL (production-ready)
Languages     : English (EN) | Swahili (SW)
Currency      : Tanzanian Shilling (TZS)
Created       : 2026
Last Updated  : August 26, 2026

================================================================================
                              OVERVIEW
================================================================================

PFAMS is a full-featured personal finance management web application built
with Django. It is designed to help individuals in Tanzania track their income,
expenses, budgets, savings goals, debts, and overall financial health — all in
one place, supporting both English and Swahili languages.

The system is built with modern web technologies offering a rich dark-mode
interface, Progressive Web App (PWA) support for offline access, and
comprehensive data analytics powered by Python's Pandas and NumPy libraries.

================================================================================
                          SYSTEM REQUIREMENTS
================================================================================

  SOFTWARE REQUIREMENTS:
  ----------------------
  - Python         : 3.10 or higher (tested on 3.12.3)
  - Django         : 5.0.6
  - pip            : Latest version recommended
  - Virtual Env    : venv (recommended)
  - Browser        : Chrome, Edge, or Firefox (latest)

  PYTHON PACKAGES (see requirements.txt):
  ----------------------------------------
  - django              >= 5.0.6
  - pillow              (image handling for profile photos)
  - pandas              (analytics engine)
  - numpy               (statistical calculations)
  - openpyxl            (Excel export)
  - reportlab           (PDF report generation)
  - whitenoise          (static files serving)

================================================================================
                         PROJECT DIRECTORY STRUCTURE
================================================================================

  truker/                          ← Root project directory
  │
  ├── personal_finance/            ← Main Django settings package
  │   ├── settings.py              ← Project configuration
  │   ├── urls.py                  ← Root URL routing
  │   └── wsgi.py / asgi.py        ← Server entry points
  │
  ├── core/                        ← Core views (dashboard, landing, switches)
  ├── accounts/                    ← User registration, login, profile
  ├── transactions/                ← Income & expense tracking
  ├── budgets/                     ← Budget planning & monitoring
  ├── goals/                       ← Savings goals & contributions
  ├── accounts_wallet/             ← Wallets, accounts & fund transfers
  ├── debts/                       ← Debt/loan tracking & repayments
  ├── notifications/               ← System alerts & notifications
  ├── reports/                     ← PDF/Excel/CSV exports & CSV import
  ├── analytics/                   ← Advanced statistical analytics
  ├── calendar_app/                ← Financial calendar & schedule
  │
  ├── templates/                   ← All HTML templates (per app)
  ├── static/                      ← CSS, JS, images, icons, SW
  ├── locale/                      ← i18n translation files
  │   └── sw/LC_MESSAGES/          ← Swahili translations
  │       ├── django.po            ← Editable translation catalog (445 msgs)
  │       └── django.mo            ← Compiled binary (auto-generated)
  │
  ├── media/                       ← User-uploaded files (receipts, photos)
  ├── compile_messages.py          ← Custom .po → .mo compiler (Windows)
  ├── manage.py                    ← Django management utility
  ├── requirements.txt             ← Python dependencies
  ├── README.txt                   ← This file
  └── FEATURE OF SYSTEM.txt        ← Full feature list

================================================================================
                          INSTALLATION & SETUP
================================================================================

  STEP 1 — Clone or Copy the Project
  ------------------------------------
  Copy the project folder to your desired location.
  Example: C:\Users\YourName\Desktop\truker\

  STEP 2 — Create a Virtual Environment
  ---------------------------------------
  Open terminal/command prompt inside the project folder and run:

      python -m venv venv

  STEP 3 — Activate the Virtual Environment
  -------------------------------------------
  Windows:
      venv\Scripts\activate

  Mac/Linux:
      source venv/bin/activate

  STEP 4 — Install Dependencies
  --------------------------------
      pip install -r requirements.txt

  STEP 5 — Apply Database Migrations
  -------------------------------------
      python manage.py migrate

  STEP 6 — Create a Superuser (Admin)
  -------------------------------------
      python manage.py createsuperuser

  STEP 7 — Load Default Categories (Optional)
  ---------------------------------------------
  If a data fixture is provided:
      python manage.py loaddata initial_categories.json

  STEP 8 — Compile Translations (Swahili)
  -----------------------------------------
      python compile_messages.py

  STEP 9 — Run the Development Server
  -------------------------------------
      python manage.py runserver

  Then open your browser and go to:
      http://127.0.0.1:8000/

================================================================================
                   HOW TO ACCESS PFAMS ON YOUR PHONE
================================================================================

  PFAMS can be accessed from any smartphone (Android or iPhone) that is
  connected to the SAME Wi-Fi network as your computer.

  ──────────────────────────────────────────────────────────────────────────
  STEP A — Find Your Computer's Local IP Address
  ──────────────────────────────────────────────────────────────────────────

  On Windows — Open Command Prompt and run:
      ipconfig

  Look for the line that says:
      IPv4 Address . . . . . . . : 192.168.x.x

  Example result: 192.168.1.105
  Write down this IP address — you will need it.

  ──────────────────────────────────────────────────────────────────────────
  STEP B — Start the Server Accessible on the Network
  ──────────────────────────────────────────────────────────────────────────

  Instead of the default runserver command, run this:

      python manage.py runserver 0.0.0.0:8000

  This makes the server accessible from ALL devices on the local network,
  not just your computer.

  !! IMPORTANT !!
  Add your computer's IP to ALLOWED_HOSTS in settings.py (or .env):
      ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.105

  Replace 192.168.1.105 with YOUR actual IP address from Step A.

  ──────────────────────────────────────────────────────────────────────────
  STEP C — Open PFAMS on Your Phone
  ──────────────────────────────────────────────────────────────────────────

  1. Connect your phone to the SAME Wi-Fi network as your computer.
  2. Open any browser on your phone (Chrome recommended).
  3. Type this address in the browser address bar:

      http://192.168.1.105:8000/

  Replace 192.168.1.105 with YOUR computer's IP from Step A.

  4. The PFAMS login page will load on your phone.
  5. Log in with your username and password.

  ──────────────────────────────────────────────────────────────────────────
  STEP D — Install PFAMS as an App on Your Phone (PWA)
  ──────────────────────────────────────────────────────────────────────────

  PFAMS is a Progressive Web App (PWA) — it can be installed on your phone
  like a native app with its own icon on your home screen.

  ON ANDROID (Chrome):
  --------------------
  1. Open PFAMS in Chrome on your phone.
  2. Tap the three-dot menu (⋮) in the top-right corner.
  3. Tap "Add to Home Screen" or "Install App".
  4. Confirm by tapping "Add" or "Install".
  5. PFAMS icon will appear on your home screen.
  6. Open it — it runs in full screen, like a native app!

  ON iPHONE (Safari):
  -------------------
  1. Open PFAMS in Safari on your iPhone.
  2. Tap the Share button (□ with arrow pointing up) at the bottom.
  3. Scroll down and tap "Add to Home Screen".
  4. Tap "Add" in the top-right corner.
  5. PFAMS icon will appear on your home screen.
  6. Open it — it runs in full screen, like a native app!

  ──────────────────────────────────────────────────────────────────────────
  STEP E — Using PFAMS Offline on Your Phone
  ──────────────────────────────────────────────────────────────────────────

  Once installed and opened at least once, PFAMS supports OFFLINE mode:

  * You can browse cached pages without internet.
  * Any transactions queued offline will sync automatically
    when your phone reconnects to the internet.
  * The connection indicator in the top bar shows:
      GREEN = Online  |  RED = Offline

  ──────────────────────────────────────────────────────────────────────────
  TROUBLESHOOTING — Phone Cannot Connect
  ──────────────────────────────────────────────────────────────────────────

  Problem: Phone shows "This site can't be reached"
  --------------------------------------------------
  ✔ Check that your computer and phone are on the SAME Wi-Fi network.
  ✔ Make sure the server is running with 0.0.0.0:8000 (not 127.0.0.1).
  ✔ Check Windows Firewall — allow Python through the firewall:
      Control Panel → Windows Defender Firewall
      → Allow an app → Find Python → Check both Private and Public.
  ✔ Confirm the IP address is correct (run ipconfig again to verify).
  ✔ Make sure DEBUG=True and the IP is in ALLOWED_HOSTS.

  Problem: Page loads but looks broken (no CSS/style)
  ----------------------------------------------------
  ✔ Make sure DEBUG=True in settings.py (dev mode serves static files).
  ✔ Try a hard refresh on the phone: hold Refresh button in Chrome.

  Problem: Login does not work on phone
  -------------------------------------
  ✔ Use the same username and password as on the computer.
  ✔ If you just created the server, make sure you ran migrations:
      python manage.py migrate

  ──────────────────────────────────────────────────────────────────────────
  QUICK SUMMARY — Phone Access Command
  ──────────────────────────────────────────────────────────────────────────

  1. Run:  python manage.py runserver 0.0.0.0:8000
  2. Find your IP: ipconfig → IPv4 Address
  3. On phone (same Wi-Fi): open http://YOUR_IP:8000/
  4. Install PWA: Add to Home Screen via browser menu



================================================================================
                         LANGUAGE SWITCHING
================================================================================

  PFAMS supports English (EN) and Swahili (SW) languages.

  To switch language:
  - Click the language button (EN/SW) in the top navigation bar
  - The selected language persists across sessions and page reloads
  - All UI text, form labels, error messages, model choices,
    and dropdown options are fully translated

  To add a new translation string:
  1. Edit: locale/sw/LC_MESSAGES/django.po
  2. Add msgid / msgstr pairs
  3. Run: python compile_messages.py

================================================================================
                         ADMIN PANEL ACCESS
================================================================================

  URL  : http://127.0.0.1:8000/admin/
  User : (the superuser you created in Step 6)

  The admin panel gives access to:
  - All users and their profiles
  - All transactions (income & expenses)
  - Categories, budgets, goals
  - Debts and repayments
  - Notifications
  - Wallet accounts and transfers

================================================================================
                      DEFAULT ADMIN CREDENTIALS
================================================================================

  The following superuser account has been pre-created for this system:

  ┌─────────────────────────────────────────────────────────────────────┐
  │   Admin Panel URL  :  http://127.0.0.1:8000/admin/                 │
  │   Username         :  admin                                         │
  │   Password         :  Admin@PFAMS2026                               │
  │   Email            :  admin@pfams.co.tz                             │
  │   Role             :  Superuser (full access)                       │
  └─────────────────────────────────────────────────────────────────────┘

  !! IMPORTANT — SECURITY WARNING !!
  -----------------------------------
  * Change the default password immediately after your first login.
  * Use the Change Password option at:
      http://127.0.0.1:8000/admin/password_change/
  * Never share these credentials with unauthorized users.
  * Before deploying to a public server, set a strong unique password
    and set DEBUG = False in settings.py.

  HOW TO CREATE ADDITIONAL ADMIN ACCOUNTS:
  ------------------------------------------
  Option 1 — From Admin Panel:
      Log in at /admin/ → Authentication → Users → Add User
      Check "Staff status" and "Superuser status" checkboxes.

  Option 2 — From Terminal:
      venv\Scripts\python.exe manage.py createsuperuser

  Option 3 — From Django Shell:
      venv\Scripts\python.exe manage.py shell -c "
      from django.contrib.auth.models import User
      User.objects.create_superuser('newadmin', 'email@example.com', 'YourPassword')
      "

================================================================================
                          TRANSLATION COMPILATION
================================================================================

  GNU gettext (msgfmt) may not be available on Windows. Use the custom
  compiler script included in the project:

      python compile_messages.py

  This script reads locale/sw/LC_MESSAGES/django.po and compiles it to
  locale/sw/LC_MESSAGES/django.mo without requiring GNU gettext tools.

  Always recompile after editing django.po.

================================================================================
                          KNOWN CONFIGURATION NOTES
================================================================================

  1. MEDIA FILES:
     Uploaded receipts, attachments, and profile photos are stored in:
         media/
     Ensure the media directory exists and is writable.

  2. STATIC FILES (Production):
     Run: python manage.py collectstatic
     WhiteNoise serves static files in production without a separate web server.

  3. DATABASE:
     Default is SQLite (db.sqlite3 in project root).
     For PostgreSQL, update DATABASES in settings.py.

  4. SECRET KEY:
     Keep SECRET_KEY in settings.py private. Never commit it to public repos.

  5. DEBUG MODE:
     Set DEBUG = False in settings.py for production deployment.

  6. ALLOWED HOSTS:
     Add your server domain/IP to ALLOWED_HOSTS in settings.py for production.

================================================================================
                            SUPPORT & CONTACT
================================================================================

  For issues, feature requests or support please contact the project owner.

  Project  : PFAMS — Personal Financial Analytics & Management System
  Country  : Tanzania
  Currency : TZS (Tanzanian Shilling)
  Version  : 1.0.0

================================================================================
                            LICENSE & USAGE
================================================================================

  This project is built for personal and educational use.
  All financial calculations are estimates and should not replace
  professional financial advice.

================================================================================
                    END OF README — PFAMS v1.0.0
================================================================================
