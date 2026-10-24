import os
import sys
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash

from database import (
    init_db,
    get_month_availability,
    get_slot_availability_for_date,
    create_appointment,
    get_appointments_by_date,
    get_appointments_history,
    update_appointment_status,
    get_admin_by_username,
    TIME_SLOTS,
    SERVICES,
    STATUSES,
    MAX_PER_SLOT
)
from validators import validate_booking_input, validate_login_input

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "gregorio_clinic_super_secret_key_2026_dev")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# --- AUTH DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            # If API request, return 401 JSON
            if request.path.startswith("/api/admin"):
                return jsonify({
                    "success": False,
                    "message": "Authentication required. Please log in as admin."
                }), 401
            # If HTML page request, redirect to login
            return redirect(url_for("admin_login_page"))
        return f(*args, **kwargs)
    return decorated_function


# --- INITIALIZE DATABASE ON STARTUP ---
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)


# ==============================================================================
# HTML VIEW ROUTES
# ==============================================================================

@app.route("/")
def index():
    """Page 1: Landing Page (Public)"""
    return render_template(
        "index.html",
        services=SERVICES,
        time_slots=TIME_SLOTS
    )


@app.route("/book")
def book_page():
    """Page 2: Appointment Booking Page (Public)"""
    today = date.today()
    return render_template(
        "book.html",
        services=SERVICES,
        time_slots=TIME_SLOTS,
        current_year=today.year,
        current_month=today.month,
        current_date_str=today.strftime("%Y-%m-%d"),
        max_per_slot=MAX_PER_SLOT
    )


@app.route("/admin/login")
def admin_login_page():
    """Page 3: Admin Login Page"""
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard_page"))
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout_page():
    """Admin Logout Route"""
    session.clear()
    return redirect(url_for("admin_login_page"))


@app.route("/admin")
@app.route("/admin/dashboard")
@login_required
def admin_dashboard_page():
    """Page 4: Admin Dashboard"""
    today = date.today()
    return render_template(
        "admin_dashboard.html",
        services=SERVICES,
        today_str=today.strftime("%Y-%m-%d"),
        admin_username=session.get("admin_username", "Administrator")
    )


@app.route("/admin/history")
@login_required
def admin_history_page():
    """Page 5: Admin History"""
    return render_template(
        "admin_history.html",
        services=SERVICES,
        statuses=STATUSES,
        admin_username=session.get("admin_username", "Administrator")
    )


# ==============================================================================
# PUBLIC API ENDPOINTS
# ==============================================================================

@app.route("/api/availability", methods=["GET"])
def api_availability():
    """
    GET /api/availability?month=YYYY-MM
    Returns per-date status (available/full/unavailable) and per-slot counts.
    """
    month_param = request.args.get("month")
    today = date.today()

    if not month_param:
        year = today.year
        month = today.month
    else:
        try:
            parts = month_param.split("-")
            year = int(parts[0])
            month = int(parts[1])
            if not (1 <= month <= 12):
                raise ValueError()
        except (ValueError, IndexError):
            return jsonify({
                "success": False,
                "message": "Invalid month format. Please use YYYY-MM."
            }), 400

    # Ensure user cannot query months prior to current month/year
    if (year < today.year) or (year == today.year and month < today.month):
        return jsonify({
            "success": False,
            "message": "Navigation to past months is not permitted."
        }), 400

    try:
        availability_data = get_month_availability(year, month)
        return jsonify({
            "success": True,
            "year": year,
            "month": month,
            "today": today.strftime("%Y-%m-%d"),
            "max_per_slot": MAX_PER_SLOT,
            "time_slots": TIME_SLOTS,
            "services": SERVICES,
            "availability": availability_data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error fetching availability: {str(e)}"
        }), 500


@app.route("/api/availability/date", methods=["GET"])
def api_date_slots():
    """
    GET /api/availability/date?date=YYYY-MM-DD
    Returns slot counts and status for a single date.
    """
    date_param = request.args.get("date")
    if not date_param:
        return jsonify({"success": False, "message": "Date parameter is required."}), 400

    try:
        parsed_date = datetime.strptime(date_param, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Expected YYYY-MM-DD."}), 400

    today = date.today()
    if parsed_date < today:
        return jsonify({"success": False, "message": "Past dates are unavailable."}), 400
    if parsed_date.weekday() == 6:
        return jsonify({"success": False, "message": "The clinic is closed on Sundays."}), 400

    try:
        slots = get_slot_availability_for_date(date_param)
        return jsonify({
            "success": True,
            "date": date_param,
            "slots": slots,
            "max_per_slot": MAX_PER_SLOT
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching date slots: {str(e)}"
        }), 500


@app.route("/api/appointments", methods=["POST"])
def api_create_appointment():
    """
    POST /api/appointments
    Create booking with strict frontend + backend validation.
    """
    payload = request.get_json(silent=True)
    print(f"\n[API] Received appointment booking request: {payload}", flush=True)

    if not payload:
        print("[API ERROR] Missing or invalid JSON payload.", flush=True)
        return jsonify({
            "success": False,
            "message": "Invalid or missing JSON payload."
        }), 400

    is_valid, errors, clean_data = validate_booking_input(payload)
    if not is_valid:
        print(f"[API] Booking validation failed: {errors}", flush=True)
        is_conflict_only = (
            ("duplicate" in errors and len(errors) == 1) or
            ("is fully booked" in errors.get("time_slot", "") and len(errors) == 1)
        )
        status_code = 409 if is_conflict_only else 400
        return jsonify({
            "success": False,
            "message": "Validation failed. Please correct the highlighted errors.",
            "errors": errors
        }), status_code

    try:
        new_appointment = create_appointment(clean_data)
        print(f"[API SUCCESS] Created appointment {new_appointment.get('reference_no')} for {new_appointment.get('full_name')} on {new_appointment.get('appointment_date')} at {new_appointment.get('time_slot')}\n", flush=True)
        return jsonify({
            "success": True,
            "message": "Appointment successfully booked!",
            "appointment": new_appointment
        }), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[API CRITICAL ERROR] Failed to save appointment: {str(e)}", flush=True)
        return jsonify({
            "success": False,
            "message": f"Failed to save appointment: {str(e)}"
        }), 500


@app.route("/api/login", methods=["POST"])
def api_login():
    """
    POST /api/login
    Admin authentication.
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"success": False, "message": "Missing credentials."}), 400

    is_valid, errors, clean_data = validate_login_input(payload)
    if not is_valid:
        return jsonify({"success": False, "errors": errors, "message": "Username and password required."}), 400

    admin = get_admin_by_username(clean_data["username"])
    if not admin or not check_password_hash(admin["password_hash"], clean_data["password"]):
        return jsonify({
            "success": False,
            "message": "Invalid username or password. Please try again."
        }), 401

    session["admin_id"] = admin["id"]
    session["admin_username"] = admin["username"]

    return jsonify({
        "success": True,
        "message": "Welcome back, Admin!",
        "redirect": url_for("admin_dashboard_page")
    }), 200


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """POST /api/logout"""
    session.clear()
    return jsonify({
        "success": True,
        "message": "Logged out successfully.",
        "redirect": url_for("admin_login_page")
    }), 200


# ==============================================================================
# PROTECTED ADMIN API ENDPOINTS
# ==============================================================================

@app.route("/api/admin/appointments", methods=["GET"])
@login_required
def api_admin_appointments():
    """
    GET /api/admin/appointments?date=YYYY-MM-DD&service=...
    Get appointments for a given date, optionally filtered by service.
    """
    date_param = request.args.get("date")
    service_param = request.args.get("service")

    if not date_param:
        date_param = date.today().strftime("%Y-%m-%d")

    try:
        appointments = get_appointments_by_date(date_param, service_param)
        return jsonify({
            "success": True,
            "date": date_param,
            "service_filter": service_param or "All",
            "count": len(appointments),
            "appointments": appointments
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error retrieving appointments: {str(e)}"
        }), 500


@app.route("/api/admin/history", methods=["GET"])
@login_required
def api_admin_history():
    """
    GET /api/admin/history?search=...&status=...
    Get all appointments with search and status filter.
    """
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    try:
        records = get_appointments_history(search_query, status_filter)
        return jsonify({
            "success": True,
            "total": len(records),
            "appointments": records
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error retrieving appointment history: {str(e)}"
        }), 500


@app.route("/api/admin/appointments/<int:appointment_id>/status", methods=["PATCH"])
@login_required
def api_admin_update_status(appointment_id):
    """
    PATCH /api/admin/appointments/<id>/status
    Payload: { "status": "Completed" | "Cancelled" }
    """
    payload = request.get_json(silent=True)
    if not payload or "status" not in payload:
        return jsonify({"success": False, "message": "Missing 'status' in payload."}), 400

    new_status = payload.get("status")
    if new_status not in ["Completed", "Cancelled", "Booked"]:
        return jsonify({
            "success": False,
            "message": f"Invalid status '{new_status}'. Allowed: Completed, Cancelled, Booked."
        }), 400

    try:
        updated = update_appointment_status(appointment_id, new_status)
        if not updated:
            return jsonify({"success": False, "message": "Appointment not found."}), 404

        return jsonify({
            "success": True,
            "message": f"Appointment status updated to '{new_status}'.",
            "appointment": updated
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating status: {str(e)}"
        }), 500


# --- ERROR HANDLERS ---
@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Endpoint not found."}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Internal server error occurred."}), 500
    return "<h3>Internal Server Error</h3><p>Please try again later.</p>", 500


if __name__ == "__main__":
    # Run development server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
