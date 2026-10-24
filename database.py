import sqlite3
import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Tests set GFC_DB_PATH to a throwaway file so they never touch the real clinic database.
DB_PATH = os.environ.get(
    "GFC_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "gregorio_clinic.db")
)

MAX_PER_SLOT = 5
TIME_SLOTS = [
    "9:00 AM - 11:00 AM",
    "1:00 PM - 3:00 PM",
    "4:00 PM - 6:00 PM"
]
SERVICES = [
    "Prenatal Checkup",
    "Ultrasound",
    "Pap Smear",
    "Well-Woman Exam"
]
STATUSES = ["Booked", "Completed", "Cancelled"]


def get_db():
    """Return an active SQLite database connection with row factory configured."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables, ensure schema migrations, and seed default admin account."""
    conn = get_db()
    cursor = conn.cursor()

    # Admins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check existing schema of appointments table
    cursor.execute("PRAGMA table_info(appointments)")
    columns = [row["name"] for row in cursor.fetchall()]

    # If old schema exists (missing first_name/last_name), drop and recreate table
    if columns and "first_name" not in columns:
        print("[DB] Migrating appointments table to new multi-name schema...")
        cursor.execute("DROP TABLE IF EXISTS appointments")

    # Create appointments table with first_name, middle_name, last_name, and full_name
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_no TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            middle_name TEXT DEFAULT '',
            last_name TEXT NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            contact_number TEXT NOT NULL,
            address TEXT NOT NULL,
            province TEXT NOT NULL,
            city TEXT NOT NULL,
            service TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Booked',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Performance indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointment_date ON appointments(appointment_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON appointments(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reference_no ON appointments(reference_no)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_full_name ON appointments(full_name)")

    # Ensure demo admin exists
    cursor.execute("SELECT id FROM admins WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        hashed_pw = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ("admin", hashed_pw)
        )
        print("[DB] Demo admin created: admin / admin123")

    conn.commit()
    conn.close()


def clear_sample_bookings():
    """Clear all sample bookings from appointments table (iteration 2 requirement)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments")
    conn.commit()
    conn.close()
    print("[DB] Cleared all sample bookings from database.")


def generate_reference_no(appointment_date_str):
    """
    Generate unique reference number format: GFC-YYYYMMDD-XXXX
    e.g., GFC-20261024-0001
    """
    clean_date = appointment_date_str.replace("-", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM appointments WHERE appointment_date = ?",
        (appointment_date_str,)
    )
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"GFC-{clean_date}-{count:04d}"


def get_month_availability(year, month):
    """
    Calculate per-date status and slot counts for a specific month.
    Statuses:
      - 'unavailable': Sunday or past date (Grey)
      - 'full': all slots are at MAX_PER_SLOT (Red)
      - 'available': at least one slot has remaining space (Green)
    """
    conn = get_db()
    cursor = conn.cursor()

    # Determine date range for month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    today = date.today()

    # Fetch active booked appointments in this month (Cancelled doesn't occupy slots)
    cursor.execute("""
        SELECT appointment_date, time_slot, COUNT(*) as booked_count
        FROM appointments
        WHERE appointment_date >= ? AND appointment_date <= ? AND status != 'Cancelled'
        GROUP BY appointment_date, time_slot
    """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))

    slot_counts = {}
    for row in cursor.fetchall():
        d = row["appointment_date"]
        slot = row["time_slot"]
        count = row["booked_count"]
        if d not in slot_counts:
            slot_counts[d] = {}
        slot_counts[d][slot] = count

    conn.close()

    availability_map = {}
    curr = start_date
    while curr <= end_date:
        d_str = curr.strftime("%Y-%m-%d")
        is_sunday = (curr.weekday() == 6)  # Sunday = 6
        is_past = (curr < today)

        # Slots breakdown
        slots_data = {}
        day_booked_total = 0
        full_slots_count = 0

        for slot in TIME_SLOTS:
            booked = slot_counts.get(d_str, {}).get(slot, 0)
            remaining = max(0, MAX_PER_SLOT - booked)
            is_full = booked >= MAX_PER_SLOT
            if is_full:
                full_slots_count += 1
            day_booked_total += booked

            slots_data[slot] = {
                "booked": booked,
                "remaining": remaining,
                "max": MAX_PER_SLOT,
                "is_full": is_full
            }

        if is_past or is_sunday:
            day_status = "unavailable"
        elif full_slots_count >= len(TIME_SLOTS):
            day_status = "full"
        else:
            day_status = "available"

        availability_map[d_str] = {
            "date": d_str,
            "day": curr.day,
            "weekday": curr.strftime("%a"),
            "status": day_status,
            "is_past": is_past,
            "is_sunday": is_sunday,
            "total_booked": day_booked_total,
            "max_possible": len(TIME_SLOTS) * MAX_PER_SLOT,
            "slots": slots_data
        }

        curr += timedelta(days=1)

    return availability_map


def get_slot_availability_for_date(date_str):
    """Return slot counts and availability status for a single date."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time_slot, COUNT(*) as booked_count
        FROM appointments
        WHERE appointment_date = ? AND status != 'Cancelled'
        GROUP BY time_slot
    """, (date_str,))

    counts = {row["time_slot"]: row["booked_count"] for row in cursor.fetchall()}
    conn.close()

    result = {}
    for slot in TIME_SLOTS:
        booked = counts.get(slot, 0)
        result[slot] = {
            "booked": booked,
            "remaining": max(0, MAX_PER_SLOT - booked),
            "max": MAX_PER_SLOT,
            "is_full": booked >= MAX_PER_SLOT
        }
    return result


def check_duplicate_booking(first_name, last_name, contact_number, appointment_date):
    """
    Check if an active (non-cancelled) booking exists for the same patient (first & last name)
    and contact number on the same date.
    Returns True if duplicate exists, False otherwise.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM appointments
        WHERE LOWER(TRIM(first_name)) = LOWER(TRIM(?))
          AND LOWER(TRIM(last_name)) = LOWER(TRIM(?))
          AND contact_number = ?
          AND appointment_date = ?
          AND status != 'Cancelled'
    """, (first_name, last_name, contact_number, appointment_date))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def create_appointment(data):
    """
    Insert a new appointment into SQLite.
    data dict contains: first_name, middle_name, last_name, age, contact_number,
    address, province, city, service, appointment_date, time_slot.
    Returns newly created appointment dict.
    """
    first = data["first_name"].strip()
    middle = data.get("middle_name", "").strip()
    last = data["last_name"].strip()
    full_name = f"{first} {middle} {last}".replace("  ", " ").strip() if middle else f"{first} {last}".strip()

    ref_no = generate_reference_no(data["appointment_date"])
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO appointments (
                reference_no, first_name, middle_name, last_name, full_name,
                age, contact_number, address, province, city,
                service, appointment_date, time_slot, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Booked')
        """, (
            ref_no,
            first,
            middle,
            last,
            full_name,
            int(data["age"]),
            data["contact_number"].strip(),
            data["address"].strip(),
            data["province"].strip(),
            data["city"].strip(),
            data["service"].strip(),
            data["appointment_date"].strip(),
            data["time_slot"].strip()
        ))

        new_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM appointments WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        return dict(row)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_appointments_by_date(date_str, service_filter=None):
    """
    Fetch appointments for a given date, optionally filtered by service.
    Returns list of dicts.
    """
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM appointments WHERE appointment_date = ?"
    params = [date_str]

    if service_filter and service_filter != "All":
        query += " AND service = ?"
        params.append(service_filter)

    query += " ORDER BY CASE time_slot WHEN '9:00 AM - 11:00 AM' THEN 1 WHEN '1:00 PM - 3:00 PM' THEN 2 WHEN '4:00 PM - 6:00 PM' THEN 3 ELSE 4 END, id ASC"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_appointments_history(search_query=None, status_filter=None):
    """
    Fetch all appointments for History view with optional search and status filter.
    Sorted by newest appointment_date DESC, id DESC.
    """
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM appointments WHERE 1=1"
    params = []

    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    if search_query:
        query += " AND (LOWER(full_name) LIKE ? OR LOWER(reference_no) LIKE ? OR contact_number LIKE ?)"
        pattern = f"%{search_query.strip().lower()}%"
        params.extend([pattern, pattern, pattern])

    query += " ORDER BY appointment_date DESC, id DESC"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_appointment_status(appointment_id, new_status):
    """
    Update appointment status (e.g. 'Completed', 'Cancelled').
    Returns updated appointment dict if found, else None.
    """
    if new_status not in STATUSES:
        return None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE appointments SET status = ? WHERE id = ?",
        (new_status, appointment_id)
    )
    conn.commit()

    cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_admin_by_username(username):
    """Fetch admin user record by username."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
