# Gregorio Family Clinic — Medical Appointment Booking System

**Implementation Specification (Build Prompt)**
S-CSSE421LA Software Engineering 2 · Laboratory 6: Design and Implementation

---

## 1. Overview

A full-stack medical appointment booking website for **Gregorio Family Clinic**. Public users book appointments through a color-coded calendar; clinic admins log in to view, manage, and track all appointments.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, vanilla JavaScript (no frameworks) |
| Backend | Python with Flask (REST API returning JSON) |
| Database | SQLite (Python's built-in `sqlite3`) |

**Code organization**
- `app.py` — routes
- `database.py` — DB setup and queries
- `validators.py` — input validation
- `static/` — CSS and JS
- `templates/` — HTML pages
- `README.md` — setup and run instructions (`pip install`, `python app.py`)

---

## 3. Design Style

- **Glassmorphism** throughout: frosted translucent cards (`backdrop-filter: blur`), soft borders, subtle shadows, over a soft gradient background.
- Calm medical palette: soft teal, blush pink, white.
- Clean, modern, readable typography.
- Fully responsive for desktop and mobile.

---

## 4. Pages

### 4.1 Landing Page (Public)

- **Header:** logo text "GREGORIO FAMILY CLINIC" (upper left); "Admin Login" button (upper right) linking to the login page.
- **Hero (center):**
  - Tagline: *"Gentle Care for Every Stage of Womanhood"*
  - Subtext: *"Book your check-up in just a few clicks."*
  - "Book an Appointment" button → Appointment page.
- **Footer (contact details):**
  - Email: gregoriofamilyclinic@gmail.com
  - Contact Number: 09979865335
  - FB: Gregorio Family Clinic

### 4.2 Appointment Page (Public)

**Calendar**
- Bento-grid style calendar of the current month, based on the real current date.
- Next/previous month navigation (cannot go to past months).
- Each date is clickable and color-coded:

| Color | Meaning |
|---|---|
| 🟢 Green | Open and available (at least one slot has space) |
| 🔴 Red | Busy / fully booked (all slots full) |
| ⚪ Grey | Not available (past dates and Sundays; not clickable) |

- A color legend is shown above the calendar.

**Booking Form** (slides/fades in when a green date is clicked, showing the selected date)

| Field | Rule |
|---|---|
| Full Name | Required; letters and spaces only; 2–60 characters |
| Age | Required; number from 1–120 |
| Contact Number | Required; PH mobile format, 11 digits starting with `09` |
| Address | Required (street/barangay) |
| Province | Required |
| City | Required |
| Schedule Time | Required; one of: 9:00 AM – 11:00 AM, 1:00 PM – 3:00 PM, 4:00 PM – 6:00 PM (full slots shown disabled as "Full") |
| Service | Required; Prenatal Checkup, Ultrasound, Pap Smear, Well-Woman Exam |

- **Book** button submits the form.
- **Capacity:** maximum of **5 appointments per time slot per date** (config constant).

**Validation (frontend AND backend)**
- Inline error messages under each invalid field.
- Backend rejects: past dates, Sundays, invalid time slots, invalid services, full slots, and duplicate bookings (same name + contact number on the same date).
- Friendly JSON error messages displayed to the user.

**On success**
- Glassmorphism pop-up modal with a thank-you message and confirmation summary: reference number, name, service, date, time.
- Calendar colors refresh immediately.
- Booking saved with status **"Booked"**, appearing instantly in the Admin Dashboard and History.

### 4.3 Admin Login

- Glassmorphism login card (username + password).
- On first run, the database auto-creates a **demo admin account**:
  - Username: `admin`
  - Password: `admin123`
  - Password stored hashed (e.g., `werkzeug.security`).
- Error message on wrong credentials.
- Flask sessions; all admin pages and admin API routes redirect/deny if not logged in.
- Logout button.

### 4.4 Admin Dashboard

- Navigation: Dashboard, History, Logout.
- **Main area:** large calendar based on the real current date (with month navigation); each date shows its number of appointments; dates are clickable.
- **Left panel:** all appointments for the selected date (defaults to today).
  - Top of panel: **Type of Service** dropdown filter (All, Prenatal Checkup, Ultrasound, Pap Smear, Well-Woman Exam).
  - Each appointment card shows, in order: Name, Age, Schedule Date, Time, Contact Number, Address, Province, City, plus a service-type badge.
  - Actions: **Mark Complete** and **Cancel** (with confirmation prompt).
  - Status updates refresh the panel, calendar, and History. Cancelled appointments free up the slot.

### 4.5 Admin History

- Table of all appointments: Name, Date, Time, Service, Status.
- Status badges:

| Status | Color |
|---|---|
| Booked | Blue |
| Completed | Green |
| Cancelled | Red |

- Search box (by name) and status filter (All, Booked, Completed, Cancelled).
- Sorted by newest date first.

---

## 5. Database Schema (SQLite)

**`admins`**

| Column | Notes |
|---|---|
| id | Primary key |
| username | Unique |
| password_hash | Hashed password |

**`appointments`**

| Column | Notes |
|---|---|
| id | Primary key |
| reference_no | Unique, e.g. `GFC-20261024-0001` |
| full_name | |
| age | |
| contact_number | |
| address | |
| province | |
| city | |
| service | |
| appointment_date | |
| time_slot | |
| status | Booked / Completed / Cancelled |
| created_at | Timestamp |

Tables and the demo admin are auto-created on startup if they don't exist.

---

## 6. API Endpoints (JSON)

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/api/availability?month=YYYY-MM` | Public | Per-date status (available/full/unavailable) and per-slot counts |
| POST | `/api/appointments` | Public | Create a booking (validated) |
| POST | `/api/login` | Public | Admin login |
| POST | `/api/logout` | Admin | Admin logout |
| GET | `/api/admin/appointments?date=YYYY-MM-DD&service=...` | Admin | Appointments for a date |
| GET | `/api/admin/history?search=...&status=...` | Admin | All appointments with filters |
| PATCH | `/api/admin/appointments/<id>/status` | Admin | Update appointment status |

---

## 7. Quality Requirements

- Error handling everywhere: `try/except` on DB operations, meaningful HTTP status codes (400, 401, 404, 409, 500), and user-friendly UI messages (never raw errors).
- Parameterized SQL queries only (no string concatenation).
- Clear code comments; small, well-named functions.
- Seed sample appointments across the current month so calendar colors and the dashboard can be demonstrated immediately.

---

## 8. Design Assumptions

| Assumption | Reason |
|---|---|
| 5 patients per time slot | Needed so dates can become fully booked (red) |
| Grey = past dates and Sundays | Clinic closed / dates no longer bookable |
| Province added to the booking form | Required by the admin dashboard layout |
| Initial status = "Booked" | Starting state before Complete/Cancel |
| Flask as the Python framework | Simplest option for a solo build |
