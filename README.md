# Gregorio Family Clinic — Medical Appointment Booking System

A full-stack, responsive medical appointment booking web application built with **Flask (Python)**, **SQLite**, and **vanilla HTML5 / CSS3 / JavaScript** featuring a calm, medical **Glassmorphism** aesthetic.

> **Tagline:** Gentle Care for Every Stage of Womanhood.  
> **Contact:** `gregoriofamilyclinic@gmail.com` | `09979865335` | FB: `Gregorio Family Clinic`

---

## 🩺 Tech Stack & Architecture

- **Backend:** Python 3 + Flask (Modular RESTful JSON API + Jinja2 Server-Side Templates)
- **Database:** SQLite (built-in `sqlite3` with parameterized queries and row factory)
- **Frontend:** Plain semantic HTML5, modern CSS3 (Glassmorphism, CSS Grid, Flexbox, backdrop-filter), and vanilla JavaScript ES6+ (no external JS/CSS frameworks)
- **Security:** Hashed passwords (`werkzeug.security` scrypt/pbkdf2), HttpOnly session cookies, parameterized SQL, comprehensive input sanitization.

### Project Structure
```text
BOOKING SYSTEM/
├── app.py                  # Main Flask application, routes, auth decorators, error handlers
├── database.py             # SQLite setup, schema definition, queries, and seed data generator
├── validators.py           # Backend input validation & business rule enforcement
├── test_system.py          # Automated integration and unit test suite
├── requirements.txt        # Python dependencies
├── README.md               # Setup, documentation, and API reference
├── static/
│   ├── css/
│   │   └── style.css       # Complete Glassmorphism styling, responsive layouts, animations
│   └── js/
│       ├── main.js         # Global toast notifications, date formatting utilities
│       ├── booking.js      # Interactive bento-grid calendar, live availability, booking modal
│       └── admin.js        # Admin calendar, appointment cards, status updates, history search
└── templates/
    ├── base.html           # Master layout with ambient blurred blobs, navigation & footer
    ├── 404.html            # Custom glassmorphic 404 error page
    ├── index.html          # Page 1: Landing Page (Public)
    ├── book.html           # Page 2: Appointment Booking Page (Public)
    ├── admin_login.html    # Page 3: Admin Login
    ├── admin_dashboard.html# Page 4: Admin Dashboard
    └── admin_history.html  # Page 5: Admin Appointment History
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- Python 3.8 or higher installed on your machine.
- Verify in your terminal:
  ```bash
  python --version
  ```

### 2. Install Dependencies
In the project directory, run:
```bash
pip install -r requirements.txt
```

### 3. Run the Application
Launch the Flask development server:
```bash
python app.py
```

The server will automatically:
1. Initialize the SQLite database (`gregorio_clinic.db`).
2. Create the `admins` and `appointments` tables with performance indexes.
3. Auto-seed the default administrator account.
4. Auto-seed sample appointments across the current month to demonstrate calendar colors (Green, Red, Grey) and admin features immediately.

Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🔐 Admin Credentials

A default administrator account is generated automatically on initial startup:
- **Username:** `admin`
- **Password:** `admin123`

Access the portal via the **Admin Login** button on the top right, or directly at:
```text
http://127.0.0.1:5000/admin/login
```

---

## 📋 Pages Overview

### Page 1: Landing Page (`/`)
- **Header:** Clinic logo text "GREGORIO FAMILY CLINIC" on top-left; "Admin Login" button on top-right.
- **Hero Section:** "Gentle Care for Every Stage of Womanhood" with subtext and prominent "Book an Appointment" CTA button.
- **Highlights & Services:** Dedicated preview cards for **Prenatal Checkup**, **Ultrasound**, **Pap Smear**, and **Well-Woman Exam**.
- **Footer:** Direct contact information (Email, Contact Number, and Facebook handle).

### Page 2: Appointment Booking (`/book`)
- **Interactive Bento-Grid Calendar:**
  - Displays the current month based on the real current date.
  - Month navigation with Next and Previous buttons (**cannot navigate to past months**).
  - Date cells color-coded by real-time capacity:
    - 🟢 **GREEN (Open & Available):** At least one slot has available capacity.
    - 🔴 **RED (Busy / Fully Booked):** All slots on that day have reached maximum capacity (5/5).
    - ⚪ **GREY (Unavailable):** Past dates and Sundays (clinic rest day; not clickable).
  - Clear color legend above the calendar.
- **Animated Booking Drawer:**
  - Smooth slide/fade transition when a green date is clicked.
  - Required fields: Full Name, Age (1-120), Contact Number (Philippine mobile: 11 digits starting with `09`), Address, Province, City, Schedule Time slot, and Service.
  - Exactly three fixed daily slots:
    1. `9:00 AM - 11:00 AM`
    2. `1:00 PM - 3:00 PM`
    3. `4:00 PM - 6:00 PM`
  - Full slots (5/5) are shown **disabled with "Full"** and cannot be selected.
  - Validates on both frontend and backend (shows inline field errors).
  - Rejects past dates, Sundays, invalid formats, full slots, and duplicate bookings (same patient name and contact number on the same date).
- **Confirmation Pop-Up Modal:**
  - Glassmorphic modal with a thank-you message and booking summary:
    - Unique reference number (e.g. `GFC-20261026-0001`)
    - Patient Name
    - Medical Service
    - Date & Time Slot
    - Contact details and preparation reminders.
  - "Copy Reference" and "Print Slip" actions.
  - Calendar availability and slot capacities refresh immediately upon booking.

### Page 3: Admin Login (`/admin/login`)
- Glassmorphic authentication card with username and password.
- Secure session management with protected routes.
- Error alerts for invalid credentials.

### Page 4: Admin Dashboard (`/admin/dashboard`)
- Top navigation bar: Dashboard, History, Patient View, and Logout.
- **Large Calendar:** Displays active appointment counts directly on each day.
- **Left Panel:** Lists all appointments for the selected date (defaults to today).
- **Service Filter:** Dropdown filter by medical service (All, Prenatal Checkup, Ultrasound, Pap Smear, Well-Woman Exam).
- **Appointment Cards:** Displays details in the required order:
  1. Full Name
  2. Age
  3. Schedule Date
  4. Time Slot
  5. Contact Number
  6. Address
  7. Province
  8. City
  *(with Service badge and reference code)*
- **Interactive Actions:**
  - `Mark Complete` button (with confirmation modal prompt).
  - `Cancel` button (with confirmation modal prompt).
  - Cancelling an appointment automatically frees up the slot and immediately updates the calendar availability.

### Page 5: Admin History (`/admin/history`)
- Comprehensive audit table of all clinic appointments sorted newest date first.
- Status badges:
  - 🔵 **Booked** (Blue)
  - 🟢 **Completed** (Green)
  - 🔴 **Cancelled** (Red)
- **Live Search Box:** Filter by patient name, reference number, or phone.
- **Status Filter Dropdown:** Filter by All, Booked, Completed, or Cancelled.
- Quick status actions directly from the table.

---

## 🔌 RESTful API Reference

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/availability?month=YYYY-MM` | Public | Returns per-date status (`available`, `full`, `unavailable`) and per-slot counts. Navigation to past months returns `400`. |
| `GET` | `/api/availability/date?date=YYYY-MM-DD` | Public | Returns slot availability and remaining capacity for a single date. |
| `POST`| `/api/appointments` | Public | Creates a new appointment booking. Validates fields, rejects duplicates & full slots. Returns `201 Created` or `400`/`409`. |
| `POST`| `/api/login` | Public | Authenticates admin credentials and initializes session cookie. |
| `POST`| `/api/logout` | Public | Terminates admin session. |
| `GET` | `/api/admin/appointments?date=...&service=...` | Admin | Fetches list of appointments for a specified date and optional service filter. |
| `GET` | `/api/admin/history?search=...&status=...` | Admin | Fetches appointments matching search string and status filter, newest first. |
| `PATCH`| `/api/admin/appointments/<id>/status` | Admin | Updates appointment status (`Completed` or `Cancelled`). |

---

## 🧪 Running Automated Tests

Run the included unit and integration test suite anytime:
```bash
python test_system.py
```

Tests cover:
- Public calendar availability & past month blocking
- Past date and Sunday restriction enforcement
- Field validation (names, ages, Philippine phone format)
- Duplicate booking rejection (`409 Conflict`)
- Admin authentication & session security
- Date & service filtering
- Appointment status lifecycle (Booked -> Completed / Cancelled)

---

## 🎨 Design Philosophy: Glassmorphism

The interface implements a frosted glass aesthetic tailored for a women's health clinic:
- Soft teal (`#0d9488`), blush pink (`#f472b6`), and pearlescent white gradient backgrounds.
- Translucent frosted glass containers using `-webkit-backdrop-filter: blur(18px)`.
- Subtle glowing orbs in the background that animate smoothly to create optical depth.
- Tactile hover states, accessible contrast ratios, and clean typography.
