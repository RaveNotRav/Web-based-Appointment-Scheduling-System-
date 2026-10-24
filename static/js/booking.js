/**
 * Gregorio Family Clinic - Booking Page Logic (Iteration 2)
 * Bento-grid calendar, availability, form validation (first/middle/last name), and modal.
 */

document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------------------
    // Real date & view state
    // -------------------------------------------------------------------------
    const realDate = new Date();
    const realYear = realDate.getFullYear();
    const realMonth = realDate.getMonth() + 1; // 1-12

    let viewYear = realYear;
    let viewMonth = realMonth;
    let selectedDateStr = null;
    let monthAvailabilityData = {};

    // -------------------------------------------------------------------------
    // DOM references
    // -------------------------------------------------------------------------
    const monthYearHeading  = document.getElementById("calendar-month-year");
    const prevMonthBtn      = document.getElementById("prev-month-btn");
    const nextMonthBtn      = document.getElementById("next-month-btn");
    const todayBtn          = document.getElementById("today-btn");
    const daysGrid          = document.getElementById("calendar-days-grid");

    const formPlaceholder   = document.getElementById("form-placeholder");
    const bookingFormCard   = document.getElementById("booking-form-card");
    const formDateDisplay   = document.getElementById("form-selected-date-display");
    const closeFormBtn      = document.getElementById("close-form-btn");

    const appointmentForm   = document.getElementById("appointment-form");
    const apptDateInput     = document.getElementById("appointment_date");
    const timeSlotSelect    = document.getElementById("time_slot");
    const submitBtn         = document.getElementById("submit-booking-btn");
    const bookingSpinner    = document.getElementById("booking-spinner");
    const generalFormError  = document.getElementById("general-form-error");

    // Modal
    const successModal      = document.getElementById("success-modal");
    const closeModalBtn     = document.getElementById("close-modal-btn");
    const printModalBtn     = document.getElementById("print-modal-btn");
    const copyRefBtn        = document.getElementById("copy-ref-btn");

    const confirmRefNo      = document.getElementById("confirm-ref-no");
    const confirmPatient    = document.getElementById("confirm-patient-name");
    const confirmService    = document.getElementById("confirm-service");
    const confirmDate       = document.getElementById("confirm-date");
    const confirmTime       = document.getElementById("confirm-time");
    const confirmContact    = document.getElementById("confirm-contact");

    const MONTH_NAMES = [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ];

    const FIXED_TIME_SLOTS = [
        "9:00 AM - 11:00 AM",
        "1:00 PM - 3:00 PM",
        "4:00 PM - 6:00 PM"
    ];

    // =========================================================================
    // CALENDAR
    // =========================================================================

    async function loadCalendar(year, month) {
        // Block past months for public view
        if (year < realYear || (year === realYear && month < realMonth)) {
            year  = realYear;
            month = realMonth;
        }
        viewYear  = year;
        viewMonth = month;

        const isPastMonthView = (viewYear === realYear && viewMonth === realMonth);
        prevMonthBtn.disabled = isPastMonthView;

        monthYearHeading.textContent = `${MONTH_NAMES[viewMonth - 1]} ${viewYear}`;

        const monthStr = `${viewYear}-${String(viewMonth).padStart(2, "0")}`;

        daysGrid.innerHTML = `
            <div style="grid-column:span 7;text-align:center;padding:2rem 0;">
                <div class="spinner" style="border-top-color:#0d9488;width:28px;height:28px;"></div>
                <p class="text-xs text-muted mt-2">Checking clinic availability…</p>
            </div>`;

        try {
            const resp = await fetch(`/api/availability?month=${monthStr}`);
            const data = await resp.json();
            if (resp.ok && data.success) {
                monthAvailabilityData = data.availability || {};
                renderDaysGrid();
            } else {
                daysGrid.innerHTML = `<div style="grid-column:span 7;text-align:center;padding:2rem;color:#e11d48;">${escapeHtml(data.message || "Error loading availability")}</div>`;
            }
        } catch {
            daysGrid.innerHTML = `<div style="grid-column:span 7;text-align:center;padding:2rem;color:#e11d48;">Failed to connect to server. Please refresh.</div>`;
        }
    }

    function renderDaysGrid() {
        daysGrid.innerHTML = "";

        const firstDay = new Date(viewYear, viewMonth - 1, 1);
        // Monday-first offset: getDay() → 0=Sun,1=Mon,…,6=Sat  →  Mon=0 offset
        let offset = firstDay.getDay() - 1;
        if (offset === -1) offset = 6;

        for (let i = 0; i < offset; i++) {
            const empty = document.createElement("div");
            empty.className = "date-cell date-cell-empty";
            empty.setAttribute("aria-hidden", "true");
            daysGrid.appendChild(empty);
        }

        const todayStr   = formatDateStr(realDate);
        const daysInMonth = new Date(viewYear, viewMonth, 0).getDate();

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${viewYear}-${String(viewMonth).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
            const info    = monthAvailabilityData[dateStr] || { status:"unavailable", total_booked:0, slots:{} };

            const cell = document.createElement("div");
            cell.className = `date-cell status-${info.status}`;
            cell.dataset.date = dateStr;

            if (dateStr === todayStr)         cell.classList.add("is-today");
            if (dateStr === selectedDateStr && info.status === "available")
                                              cell.classList.add("is-selected");

            let label = "", sub = "";
            if (info.status === "available") {
                label = "Open";
                sub   = `${15 - (info.total_booked || 0)} left`;
                cell.setAttribute("tabindex", "0");
                cell.setAttribute("role", "button");
                cell.setAttribute("aria-label", `${formatReadableDate(dateStr)}, Open`);
            } else if (info.status === "full") {
                label = "Full";
                sub   = "Fully booked";
            } else {
                label = info.is_sunday ? "Closed" : "Past";
                sub   = info.is_sunday ? "Sunday"  : "Past date";
            }

            cell.innerHTML = `
                <div class="flex-between">
                    <span class="cell-day-number">${day}</span>
                    <span class="cell-status-label">${label}</span>
                </div>
                <div class="cell-slot-count">${sub}</div>`;

            if (info.status === "available") {
                const handler = () => handleDateSelect(dateStr, info);
                cell.addEventListener("click", handler);
                cell.addEventListener("keydown", (e) => {
                    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handler(); }
                });
            }

            daysGrid.appendChild(cell);
        }
    }

    function handleDateSelect(dateStr, dayInfo) {
        selectedDateStr = dateStr;

        document.querySelectorAll(".date-cell").forEach(c => c.classList.remove("is-selected"));
        const cell = document.querySelector(`.date-cell[data-date="${dateStr}"]`);
        if (cell) cell.classList.add("is-selected");

        apptDateInput.value     = dateStr;
        formDateDisplay.textContent = formatReadableDate(dateStr);

        updateTimeSlotDropdown(dayInfo.slots || {});

        formPlaceholder.classList.add("hidden");
        bookingFormCard.classList.remove("hidden");
        clearAllErrors();

        if (window.innerWidth < 980) {
            bookingFormCard.scrollIntoView({ behavior:"smooth", block:"start" });
        }
    }

    function updateTimeSlotDropdown(slotsData) {
        timeSlotSelect.innerHTML = `<option value="">-- Choose an Available Time Slot --</option>`;
        const parts = [];

        FIXED_TIME_SLOTS.forEach(slot => {
            const s   = slotsData[slot] || { booked:0, remaining:5, is_full:false };
            const opt = document.createElement("option");
            opt.value = slot;

            if (s.is_full || s.booked >= 5) {
                opt.disabled     = true;
                opt.textContent  = `${slot} — Full (0/5 slots)`;
                parts.push(`<span style="color:#e11d48;font-weight:600;">${slot}: Full</span>`);
            } else {
                const left      = 5 - s.booked;
                opt.textContent = `${slot} (${left} available)`;
                parts.push(`<span>${slot}: <strong>${left}/5 open</strong></span>`);
            }

            timeSlotSelect.appendChild(opt);
        });

    }

    // Close form
    closeFormBtn.addEventListener("click", () => {
        bookingFormCard.classList.add("hidden");
        formPlaceholder.classList.remove("hidden");
        selectedDateStr = null;
        document.querySelectorAll(".date-cell").forEach(c => c.classList.remove("is-selected"));
    });

    // Month navigation
    prevMonthBtn.addEventListener("click", () => {
        if (prevMonthBtn.disabled) return;
        let m = viewMonth - 1, y = viewYear;
        if (m < 1) { m = 12; y--; }
        loadCalendar(y, m);
    });

    nextMonthBtn.addEventListener("click", () => {
        let m = viewMonth + 1, y = viewYear;
        if (m > 12) { m = 1; y++; }
        loadCalendar(y, m);
    });

    todayBtn.addEventListener("click", () => loadCalendar(realYear, realMonth));

    // =========================================================================
    // FORM VALIDATION (client-side)
    // =========================================================================

    const NAME_REGEX    = /^[A-Za-z\s.\-]{1,100}$/;
    const CONTACT_REGEX = /^09\d{9}$/;

    function clearAllErrors() {
        document.querySelectorAll(".inline-error").forEach(el => el.textContent = "");
        document.querySelectorAll(".form-control").forEach(el => el.classList.remove("is-invalid"));
        generalFormError.classList.add("hidden");
        generalFormError.textContent = "";
    }

    function setErr(fieldId, msg) {
        const errEl = document.getElementById(`error-${fieldId}`);
        const inp   = document.getElementById(fieldId);
        if (errEl) errEl.textContent = msg;
        if (inp)   inp.classList.add("is-invalid");
    }

    function validateForm(data) {
        clearAllErrors();
        let ok = true;

        // First Name
        if (!data.first_name) {
            setErr("first_name", "First name is required."); ok = false;
        } else if (data.first_name.length > 100) {
            setErr("first_name", "First name must be 100 characters or fewer."); ok = false;
        } else if (!NAME_REGEX.test(data.first_name)) {
            setErr("first_name", "First name must contain letters and spaces only."); ok = false;
        }

        // Middle Name (optional)
        if (data.middle_name && data.middle_name.length > 100) {
            setErr("middle_name", "Middle name must be 100 characters or fewer."); ok = false;
        } else if (data.middle_name && !NAME_REGEX.test(data.middle_name)) {
            setErr("middle_name", "Middle name must contain letters and spaces only."); ok = false;
        }

        // Last Name
        if (!data.last_name) {
            setErr("last_name", "Last name is required."); ok = false;
        } else if (data.last_name.length > 100) {
            setErr("last_name", "Last name must be 100 characters or fewer."); ok = false;
        } else if (!NAME_REGEX.test(data.last_name)) {
            setErr("last_name", "Last name must contain letters and spaces only."); ok = false;
        }

        // Age
        if (!data.age) {
            setErr("age", "Age is required."); ok = false;
        } else {
            const n = parseInt(data.age, 10);
            if (isNaN(n) || n < 1 || n > 120) { setErr("age", "Age must be between 1 and 120."); ok = false; }
        }

        // Contact Number
        if (!data.contact_number) {
            setErr("contact_number", "Contact number is required."); ok = false;
        } else if (!CONTACT_REGEX.test(data.contact_number.replace(/\s|-/g, ""))) {
            setErr("contact_number", "Please enter a valid 11-digit Philippine mobile number starting with 09 (e.g. 09171234567)."); ok = false;
        }

        // Address
        if (!data.address) {
            setErr("address", "Address is required."); ok = false;
        } else if (data.address.length < 3) {
            setErr("address", "Address is too short (min 3 characters)."); ok = false;
        }

        // Province
        if (!data.province) { setErr("province", "Province is required."); ok = false; }
        else if (data.province.length < 2) { setErr("province", "Province must be at least 2 characters."); ok = false; }

        // City
        if (!data.city) { setErr("city", "City/municipality is required."); ok = false; }
        else if (data.city.length < 2) { setErr("city", "City must be at least 2 characters."); ok = false; }

        // Time slot
        if (!data.time_slot) { setErr("time_slot", "Please select an available TIME slot."); ok = false; }

        // Service
        if (!data.service) { setErr("service", "Please select a medical service."); ok = false; }

        // Date (set by calendar click)
        if (!data.appointment_date) {
            generalFormError.textContent = "Please pick a date from the calendar.";
            generalFormError.classList.remove("hidden");
            ok = false;
        }

        return ok;
    }

    // Live clear on contact input: strip non-digits
    document.getElementById("contact_number").addEventListener("input", (e) => {
        e.target.value = e.target.value.replace(/\D/g, "");
        const errEl = document.getElementById("error-contact_number");
        if (errEl && errEl.textContent && CONTACT_REGEX.test(e.target.value)) {
            errEl.textContent = "";
            e.target.classList.remove("is-invalid");
        }
    });

    // =========================================================================
    // FORM SUBMISSION — sends first_name / middle_name / last_name to backend
    // =========================================================================

    appointmentForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        console.log("[Booking] Form submit triggered.");

        // Collect values from 3-name fields
        const first  = (document.getElementById("first_name")?.value  || "").trim();
        const middle = (document.getElementById("middle_name")?.value  || "").trim();
        const last   = (document.getElementById("last_name")?.value    || "").trim();

        const payload = {
            appointment_date: apptDateInput.value.trim(),
            first_name:       first,
            middle_name:      middle,
            last_name:        last,
            age:              (document.getElementById("age")?.value || "").trim(),
            contact_number:   (document.getElementById("contact_number")?.value || "").trim(),
            address:          (document.getElementById("address")?.value || "").trim(),
            province:         (document.getElementById("province")?.value || "").trim(),
            city:             (document.getElementById("city")?.value || "").trim(),
            time_slot:        timeSlotSelect.value.trim(),
            service:          (document.getElementById("service")?.value || "").trim()
        };

        console.log("[Booking] Payload:", payload);

        if (!validateForm(payload)) {
            console.log("[Booking] Client-side validation failed.");
            revealFirstError();
            showToast("Please complete the highlighted fields.", "error");
            return;
        }

        // Lock submit button
        submitBtn.disabled = true;
        bookingSpinner.classList.remove("hidden");
        const btnText = submitBtn.querySelector(".btn-text");
        btnText.textContent = "Booking Your Appointment…";

        try {
            const resp = await fetch("/api/appointments", {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify(payload)
            });

            // If the page was opened outside Flask (file://, Live Server, a preview port),
            // the API answers with HTML or nothing. Say so instead of failing silently.
            let data;
            try {
                data = await resp.json();
            } catch {
                throw new Error("NON_JSON");
            }
            console.log("[Booking] Server response:", resp.status, data);

            if (resp.status === 201 && data.success) {
                const appt = data.appointment;

                // Populate confirmation modal
                confirmRefNo.textContent   = appt.reference_no;
                confirmPatient.textContent = appt.full_name;
                confirmService.textContent = appt.service;
                confirmDate.textContent    = formatReadableDate(appt.appointment_date);
                confirmTime.textContent    = appt.time_slot;
                confirmContact.textContent = appt.contact_number;

                // Show modal, reset form, close drawer
                successModal.classList.remove("hidden");
                appointmentForm.reset();
                bookingFormCard.classList.add("hidden");
                formPlaceholder.classList.remove("hidden");
                selectedDateStr = null;

                // Refresh calendar colours immediately
                await loadCalendar(viewYear, viewMonth);
                showToast("Appointment successfully booked!", "success");

            } else {
                // Show backend errors
                if (data.errors) {
                    Object.entries(data.errors).forEach(([field, msg]) => {
                        const hasField = document.getElementById(`error-${field}`);
                        if (field === "duplicate" || field === "general" || !hasField) {
                            // Unknown keys go to the banner so no error is ever invisible.
                            generalFormError.textContent = msg;
                            generalFormError.classList.remove("hidden");
                        } else {
                            setErr(field, msg);
                        }
                    });
                    revealFirstError();
                } else {
                    generalFormError.textContent = data.message || "An error occurred. Please try again.";
                    generalFormError.classList.remove("hidden");
                    revealFirstError();
                }
                showToast(data.message || "Please correct the highlighted errors.", "error");
            }

        } catch (err) {
            console.error("[Booking] Network/fetch error:", err);
            generalFormError.textContent = (err && err.message === "NON_JSON")
                ? "The booking server did not respond correctly. Make sure the site is opened from http://127.0.0.1:5000 while python app.py is running."
                : "Cannot reach the booking server. Make sure python app.py is running, then try again.";
            generalFormError.classList.remove("hidden");
            revealFirstError();
            showToast("Network error. Please try again.", "error");
        } finally {
            submitBtn.disabled = false;
            bookingSpinner.classList.add("hidden");
            btnText.textContent = "Confirm & Book Appointment";
        }
    });

    // =========================================================================
    // MODAL ACTIONS
    // =========================================================================

    closeModalBtn.addEventListener("click", () => successModal.classList.add("hidden"));

    successModal.addEventListener("click", (e) => {
        if (e.target === successModal) successModal.classList.add("hidden");
    });

    copyRefBtn.addEventListener("click", () => {
        const text = confirmRefNo.textContent;
        navigator.clipboard.writeText(text)
            .then(() => showToast("Reference number copied!", "success"))
            .catch(() => showToast("Reference: " + text, "info"));
    });

    printModalBtn.addEventListener("click", () => window.print());

    // =========================================================================
    // HELPERS
    // =========================================================================

    // The form scrolls inside its card, so an error near the top can be out of
    // sight when the user presses Book. Scroll to the first problem and focus it.
    function revealFirstError() {
        const firstInvalid = appointmentForm.querySelector(".form-control.is-invalid");
        const target = firstInvalid || (!generalFormError.classList.contains("hidden") ? generalFormError : null);
        if (!target) return;
        target.scrollIntoView({ behavior: "smooth", block: "center" });
        if (firstInvalid) firstInvalid.focus({ preventScroll: true });
    }

    function formatDateStr(d) {
        return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
    }

    // Initial load
    loadCalendar(viewYear, viewMonth);
});
