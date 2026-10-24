import re
from datetime import datetime, date
from database import TIME_SLOTS, SERVICES, MAX_PER_SLOT, get_slot_availability_for_date, check_duplicate_booking

NAME_PATTERN = re.compile(r"^[A-Za-z\s\.\-]{1,100}$")
CONTACT_NUMBER_PATTERN = re.compile(r"^09\d{9}$")


def validate_booking_input(data):
    """
    Validate all inputs for an appointment booking.
    Updated for Iteration 2:
      - First Name (required, up to 100 chars)
      - Middle Name (optional, up to 100 chars)
      - Last Name (required, up to 100 chars)
      - Address (required, up to 255 chars)
      - Province / City (required, up to 100 chars each)
    Returns: (is_valid: bool, errors: dict, clean_data: dict)
    """
    errors = {}
    clean_data = {}

    if not isinstance(data, dict):
        return False, {"general": "Invalid request payload format."}, {}

    # 1. First Name
    raw_first = data.get("first_name", "")
    if not isinstance(raw_first, str) or not raw_first.strip():
        errors["first_name"] = "First name is required."
    else:
        first = " ".join(raw_first.strip().split())
        if len(first) < 1 or len(first) > 100:
            errors["first_name"] = "First name must be between 1 and 100 characters."
        elif not NAME_PATTERN.match(first):
            errors["first_name"] = "First name must contain letters and spaces only."
        else:
            clean_data["first_name"] = first

    # 2. Middle Name (Optional)
    raw_middle = data.get("middle_name", "")
    if isinstance(raw_middle, str) and raw_middle.strip():
        middle = " ".join(raw_middle.strip().split())
        if len(middle) > 100:
            errors["middle_name"] = "Middle name must not exceed 100 characters."
        elif not NAME_PATTERN.match(middle):
            errors["middle_name"] = "Middle name must contain letters and spaces only."
        else:
            clean_data["middle_name"] = middle
    else:
        clean_data["middle_name"] = ""

    # 3. Last Name
    raw_last = data.get("last_name", "")
    if not isinstance(raw_last, str) or not raw_last.strip():
        errors["last_name"] = "Last name is required."
    else:
        last = " ".join(raw_last.strip().split())
        if len(last) < 1 or len(last) > 100:
            errors["last_name"] = "Last name must be between 1 and 100 characters."
        elif not NAME_PATTERN.match(last):
            errors["last_name"] = "Last name must contain letters and spaces only."
        else:
            clean_data["last_name"] = last

    # Compute full_name if first and last name are valid
    if "first_name" in clean_data and "last_name" in clean_data:
        m = clean_data.get("middle_name", "").strip()
        f = clean_data["first_name"].strip()
        l = clean_data["last_name"].strip()
        clean_data["full_name"] = f"{f} {m} {l}".replace("  ", " ").strip() if m else f"{f} {l}".strip()

    # 4. Age
    raw_age = data.get("age")
    if raw_age is None or str(raw_age).strip() == "":
        errors["age"] = "Age is required."
    else:
        try:
            age_int = int(raw_age)
            if age_int < 1 or age_int > 120:
                errors["age"] = "Age must be a valid number between 1 and 120."
            else:
                clean_data["age"] = age_int
        except (ValueError, TypeError):
            errors["age"] = "Age must be a valid whole number."

    # 5. Contact Number (Philippine mobile: 11 digits starting with 09)
    raw_contact = data.get("contact_number", "")
    if not isinstance(raw_contact, str) or not raw_contact.strip():
        errors["contact_number"] = "Contact number is required."
    else:
        contact = raw_contact.strip().replace(" ", "").replace("-", "")
        if not CONTACT_NUMBER_PATTERN.match(contact):
            errors["contact_number"] = "Please enter a valid 11-digit Philippine mobile number starting with 09 (e.g. 09171234567)."
        else:
            clean_data["contact_number"] = contact

    # 6. Address (Up to 255 characters)
    raw_address = data.get("address", "")
    if not isinstance(raw_address, str) or not raw_address.strip():
        errors["address"] = "Address (street / barangay) is required."
    elif len(raw_address.strip()) < 3 or len(raw_address.strip()) > 255:
        errors["address"] = "Address must be between 3 and 255 characters."
    else:
        clean_data["address"] = raw_address.strip()

    # 7. Province (Up to 100 characters)
    raw_province = data.get("province", "")
    if not isinstance(raw_province, str) or not raw_province.strip():
        errors["province"] = "Province is required."
    elif len(raw_province.strip()) < 2 or len(raw_province.strip()) > 100:
        errors["province"] = "Province must be between 2 and 100 characters."
    else:
        clean_data["province"] = raw_province.strip()

    # 8. City (Up to 100 characters)
    raw_city = data.get("city", "")
    if not isinstance(raw_city, str) or not raw_city.strip():
        errors["city"] = "City / Municipality is required."
    elif len(raw_city.strip()) < 2 or len(raw_city.strip()) > 100:
        errors["city"] = "City must be between 2 and 100 characters."
    else:
        clean_data["city"] = raw_city.strip()

    # 9. Service
    raw_service = data.get("service", "")
    if not raw_service or raw_service not in SERVICES:
        errors["service"] = f"Please select a valid service ({', '.join(SERVICES)})."
    else:
        clean_data["service"] = raw_service

    # 10. Appointment Date
    raw_date = data.get("appointment_date", "")
    parsed_date = None
    if not raw_date or not isinstance(raw_date, str):
        errors["appointment_date"] = "Appointment date is required."
    else:
        try:
            parsed_date = datetime.strptime(raw_date.strip(), "%Y-%m-%d").date()
            today = date.today()
            if parsed_date < today:
                errors["appointment_date"] = "Appointments cannot be booked for past dates."
            elif parsed_date.weekday() == 6:  # Sunday
                errors["appointment_date"] = "The clinic is closed on Sundays. Please select Monday to Saturday."
            else:
                clean_data["appointment_date"] = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            errors["appointment_date"] = "Invalid date format. Expected YYYY-MM-DD."

    # 11. Schedule Time Slot
    raw_slot = data.get("time_slot", "")
    if not raw_slot or raw_slot not in TIME_SLOTS:
        errors["time_slot"] = f"Please select a valid TIME slot ({', '.join(TIME_SLOTS)})."
    else:
        clean_data["time_slot"] = raw_slot

    # If basic field checks passed for date and slot, check slot capacity
    if "appointment_date" in clean_data and "time_slot" in clean_data:
        slot_status = get_slot_availability_for_date(clean_data["appointment_date"])
        selected_slot_info = slot_status.get(clean_data["time_slot"])
        if selected_slot_info and selected_slot_info["is_full"]:
            errors["time_slot"] = f"The selected TIME slot ({clean_data['time_slot']}) is fully booked on this date. Please choose another TIME slot or date."

    # Duplicate check: same first name + last name + contact number on the same date
    if "first_name" in clean_data and "last_name" in clean_data and "contact_number" in clean_data and "appointment_date" in clean_data:
        if check_duplicate_booking(clean_data["first_name"], clean_data["last_name"], clean_data["contact_number"], clean_data["appointment_date"]):
            errors["duplicate"] = f"A booking under {clean_data['full_name']} with contact {clean_data['contact_number']} already exists on {clean_data['appointment_date']}."

    is_valid = len(errors) == 0
    return is_valid, errors, clean_data


def validate_login_input(data):
    """
    Validate admin login credentials.
    Returns: (is_valid: bool, errors: dict, clean_data: dict)
    """
    errors = {}
    clean_data = {}

    if not isinstance(data, dict):
        return False, {"general": "Invalid credentials format."}, {}

    username = data.get("username", "")
    password = data.get("password", "")

    if not isinstance(username, str) or not username.strip():
        errors["username"] = "Username is required."
    else:
        clean_data["username"] = username.strip()

    if not isinstance(password, str) or not password:
        errors["password"] = "Password is required."
    else:
        clean_data["password"] = password

    return len(errors) == 0, errors, clean_data
