"""
Gregorio Family Clinic - Full test suite.

Runs on a TEMPORARY database, so it never touches gregorio_clinic.db.

Run with either:
    python -m pytest -v test_app.py
    python test_app.py
"""
import os
import tempfile
import unittest
from datetime import date, timedelta

# Point the app at a throwaway database BEFORE importing it.
_TMP_DIR = tempfile.mkdtemp(prefix="gfc_test_")
os.environ["GFC_DB_PATH"] = os.path.join(_TMP_DIR, "test.db")

import database  # noqa: E402
from app import app  # noqa: E402
from database import TIME_SLOTS, SERVICES, MAX_PER_SLOT, init_db  # noqa: E402


def next_open_day(start_offset=1):
    """Return the next non-Sunday date at least start_offset days from today."""
    d = date.today() + timedelta(days=start_offset)
    while d.weekday() == 6:
        d += timedelta(days=1)
    return d


def valid_payload(**overrides):
    data = {
        "first_name": "Maria",
        "middle_name": "Clara",
        "last_name": "Santos",
        "age": 28,
        "contact_number": "09171234567",
        "address": "123 Rizal Street, Brgy. San Antonio",
        "province": "Cavite",
        "city": "Dasmarinas",
        "service": SERVICES[0],
        "appointment_date": next_open_day().strftime("%Y-%m-%d"),
        "time_slot": TIME_SLOTS[0],
    }
    data.update(overrides)
    return data


class ClinicTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        # Fresh empty tables for every test.
        if os.path.exists(database.DB_PATH):
            os.remove(database.DB_PATH)
        init_db()
        self.client = app.test_client()

    def login(self):
        return self.client.post("/api/login", json={"username": "admin", "password": "admin123"})

    def book(self, **overrides):
        return self.client.post("/api/appointments", json=valid_payload(**overrides))

    # ---------- Safety ----------
    def test_uses_temporary_database(self):
        self.assertNotIn("gregorio_clinic.db", database.DB_PATH)

    # ---------- Pages ----------
    def test_public_pages_load(self):
        for path in ["/", "/book", "/admin/login"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_admin_pages_require_login(self):
        for path in ["/admin/dashboard", "/admin/history"]:
            self.assertEqual(self.client.get(path).status_code, 302, path)

    def test_booking_form_has_iteration2_fields(self):
        html = self.client.get("/book").get_data(as_text=True)
        for field in ["first_name", "middle_name", "last_name", "province", "time_slot"]:
            self.assertIn(f'id="{field}"', html)
        self.assertNotIn("11-digit PH mobile starting with 09", html)

    # ---------- Availability ----------
    def test_availability_all_open_when_empty(self):
        month = next_open_day().strftime("%Y-%m")
        data = self.client.get(f"/api/availability?month={month}").get_json()
        self.assertTrue(data["success"])
        for d, info in data["availability"].items():
            if not info["is_past"] and not info["is_sunday"]:
                self.assertEqual(info["status"], "available", d)

    def test_past_month_rejected(self):
        self.assertEqual(self.client.get("/api/availability?month=2020-01").status_code, 400)

    # ---------- Booking (the reported bug) ----------
    def test_booking_saves_to_database(self):
        r = self.book()
        self.assertEqual(r.status_code, 201, r.get_json())
        appt = r.get_json()["appointment"]
        self.assertEqual(appt["full_name"], "Maria Clara Santos")
        self.assertEqual(appt["status"], "Booked")
        self.assertTrue(appt["reference_no"].startswith("GFC-"))

        conn = database.get_db()
        count = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_booking_without_middle_name(self):
        r = self.book(middle_name="")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["appointment"]["full_name"], "Maria Santos")

    def test_booking_appears_in_admin_dashboard_and_history(self):
        appt = self.book().get_json()["appointment"]
        self.login()
        day = self.client.get(f"/api/admin/appointments?date={appt['appointment_date']}").get_json()
        self.assertEqual(day["count"], 1)
        hist = self.client.get("/api/admin/history").get_json()
        self.assertEqual(hist["total"], 1)

    def test_long_text_fields_accepted(self):
        r = self.book(first_name="A" * 100, last_name="B" * 100,
                      address="X" * 255, province="P" * 100, city="C" * 100)
        self.assertEqual(r.status_code, 201, r.get_json())

    # ---------- Validation ----------
    def test_missing_required_fields(self):
        r = self.book(first_name="", last_name="", age="", contact_number="")
        self.assertEqual(r.status_code, 400)
        errors = r.get_json()["errors"]
        for f in ["first_name", "last_name", "age", "contact_number"]:
            self.assertIn(f, errors)

    def test_invalid_contact_number(self):
        for bad in ["0917123456", "08171234567", "abcdefghijk"]:
            self.assertEqual(self.book(contact_number=bad).status_code, 400, bad)

    def test_invalid_age(self):
        for bad in [0, 121, "abc"]:
            self.assertEqual(self.book(age=bad).status_code, 400, bad)

    def test_too_long_fields_rejected(self):
        self.assertEqual(self.book(first_name="A" * 101).status_code, 400)
        self.assertEqual(self.book(address="X" * 256).status_code, 400)

    def test_past_date_and_sunday_rejected(self):
        past = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertEqual(self.book(appointment_date=past).status_code, 400)
        sunday = date.today() + timedelta(days=(6 - date.today().weekday()) % 7 or 7)
        self.assertEqual(self.book(appointment_date=sunday.strftime("%Y-%m-%d")).status_code, 400)

    def test_invalid_slot_and_service_rejected(self):
        self.assertEqual(self.book(time_slot="7:00 PM - 8:00 PM").status_code, 400)
        self.assertEqual(self.book(service="Dental").status_code, 400)

    def test_duplicate_booking_rejected(self):
        self.assertEqual(self.book().status_code, 201)
        r = self.book()
        self.assertEqual(r.status_code, 409)
        self.assertIn("duplicate", r.get_json()["errors"])

    def test_slot_becomes_full(self):
        for i in range(MAX_PER_SLOT):
            r = self.book(first_name=f"Patient{'abcdefghij'[i]}", contact_number=f"0917123450{i}")
            self.assertEqual(r.status_code, 201)
        r = self.book(first_name="Extra", contact_number="09179999999")
        self.assertEqual(r.status_code, 409)

    def test_day_turns_red_when_all_slots_full(self):
        target = valid_payload()["appointment_date"]
        n = 0
        for slot in TIME_SLOTS:
            for i in range(MAX_PER_SLOT):
                n += 1
                r = self.book(time_slot=slot, first_name="Pt" + "abcdefghijklmnopqrstuvwxyz"[n % 26] * 2,
                              contact_number=f"0917{n:07d}")
                self.assertEqual(r.status_code, 201, r.get_json())
        data = self.client.get(f"/api/availability?month={target[:7]}").get_json()
        self.assertEqual(data["availability"][target]["status"], "full")

    # ---------- Admin ----------
    def test_login_wrong_password(self):
        r = self.client.post("/api/login", json={"username": "admin", "password": "wrong"})
        self.assertEqual(r.status_code, 401)

    def test_admin_api_requires_login(self):
        self.assertEqual(self.client.get("/api/admin/history").status_code, 401)

    def test_mark_complete_and_cancel(self):
        appt = self.book().get_json()["appointment"]
        self.login()
        url = f"/api/admin/appointments/{appt['id']}/status"
        r = self.client.patch(url, json={"status": "Completed"})
        self.assertEqual(r.get_json()["appointment"]["status"], "Completed")
        r = self.client.patch(url, json={"status": "Cancelled"})
        self.assertEqual(r.get_json()["appointment"]["status"], "Cancelled")

    def test_cancel_frees_slot(self):
        appt = self.book().get_json()["appointment"]
        self.login()
        self.client.patch(f"/api/admin/appointments/{appt['id']}/status", json={"status": "Cancelled"})
        slots = self.client.get(f"/api/availability/date?date={appt['appointment_date']}").get_json()["slots"]
        self.assertEqual(slots[TIME_SLOTS[0]]["booked"], 0)

    def test_history_search_and_filter(self):
        self.book()
        self.book(first_name="Ana", last_name="Reyes", contact_number="09181234567")
        self.login()
        self.assertEqual(self.client.get("/api/admin/history?search=reyes").get_json()["total"], 1)
        self.assertEqual(self.client.get("/api/admin/history?status=Completed").get_json()["total"], 0)

    def test_no_sample_bookings_on_startup(self):
        conn = database.get_db()
        count = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
