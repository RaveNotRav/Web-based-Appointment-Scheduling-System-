/**
 * Gregorio Family Clinic - Admin Dashboard & History Logic (Iteration 2)
 * - Fixed refresh button (reloads both calendar and panel)
 * - Updated appointment cards to show first_name / middle_name / last_name
 * - Removed "Patient View" tab logic
 */

document.addEventListener("DOMContentLoaded", () => {
    const isDashboard = document.getElementById("admin-calendar-grid") !== null;
    const isHistory   = document.getElementById("history-table-body")  !== null;

    if (isDashboard) initAdminDashboard();
    if (isHistory)   initAdminHistory();
});

// =============================================================================
// ADMIN DASHBOARD
// =============================================================================
function initAdminDashboard() {
    const realDate  = new Date();
    const realYear  = realDate.getFullYear();
    const realMonth = realDate.getMonth() + 1;

    let adminYear  = realYear;
    let adminMonth = realMonth;
    let selectedDate = `${realDate.getFullYear()}-${String(realDate.getMonth() + 1).padStart(2, "0")}-${String(realDate.getDate()).padStart(2, "0")}`;

    // DOM refs
    const monthHeading   = document.getElementById("admin-calendar-month-year");
    const prevBtn        = document.getElementById("admin-prev-month");
    const nextBtn        = document.getElementById("admin-next-month");
    const todayBtn       = document.getElementById("admin-today-btn");
    const calGrid        = document.getElementById("admin-calendar-grid");

    const dateHeading    = document.getElementById("selected-date-heading");
    const dateSub        = document.getElementById("selected-date-sub");
    const serviceFilter  = document.getElementById("service-filter");
    const apptContainer  = document.getElementById("appointments-list-container");
    const countText      = document.getElementById("panel-count-text");
    const refreshBtn     = document.getElementById("refresh-panel-btn");

    // Confirmation modal
    const confirmModal   = document.getElementById("status-confirm-modal");
    const confirmTitle   = document.getElementById("confirm-modal-title");
    const confirmDesc    = document.getElementById("confirm-modal-desc");
    const confirmIcon    = document.getElementById("confirm-modal-icon");
    const proceedBtn     = document.getElementById("confirm-modal-proceed-btn");
    const cancelModalBtn = document.getElementById("confirm-modal-cancel-btn");

    let pendingAction = null;

    const MONTH_NAMES = [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ];

    // -------------------------------------------------------------------------
    // Calendar
    // -------------------------------------------------------------------------
    async function loadAdminCalendar(year, month) {
        adminYear  = year;
        adminMonth = month;
        monthHeading.textContent = `${MONTH_NAMES[adminMonth - 1]} ${adminYear}`;

        const monthStr = `${adminYear}-${String(adminMonth).padStart(2, "0")}`;
        calGrid.innerHTML = `
            <div style="grid-column:span 7;text-align:center;padding:2rem 0;">
                <div class="spinner" style="border-top-color:#0d9488;width:24px;height:24px;"></div>
                <p class="text-xs text-muted mt-2">Loading…</p>
            </div>`;

        try {
            const resp = await fetch(`/api/availability?month=${monthStr}`);
            const data = await resp.json();
            if (resp.ok && data.success) {
                renderAdminCalGrid(data.availability || {});
            } else {
                calGrid.innerHTML = `<div style="grid-column:span 7;text-align:center;padding:2rem;color:#e11d48;">Failed to load calendar.</div>`;
            }
        } catch {
            calGrid.innerHTML = `<div style="grid-column:span 7;text-align:center;padding:2rem;color:#e11d48;">Network error.</div>`;
        }
    }

    function renderAdminCalGrid(availMap) {
        calGrid.innerHTML = "";

        const firstDay = new Date(adminYear, adminMonth - 1, 1);
        let offset = firstDay.getDay() - 1;
        if (offset === -1) offset = 6;

        for (let i = 0; i < offset; i++) {
            const empty = document.createElement("div");
            empty.className = "admin-date-cell date-cell-empty";
            calGrid.appendChild(empty);
        }

        const todayStr    = `${realDate.getFullYear()}-${String(realDate.getMonth()+1).padStart(2,"0")}-${String(realDate.getDate()).padStart(2,"0")}`;
        const daysInMonth = new Date(adminYear, adminMonth, 0).getDate();

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${adminYear}-${String(adminMonth).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
            const info    = availMap[dateStr] || { total_booked:0, is_sunday:false, status:"available" };

            const cell = document.createElement("div");
            cell.className    = "admin-date-cell";
            cell.dataset.date = dateStr;

            if (dateStr === selectedDate) cell.classList.add("is-selected-date");
            if (info.is_sunday)           cell.classList.add("is-sunday");
            else if (info.status === "full") cell.classList.add("is-full-day");
            else if (info.total_booked > 0)  cell.classList.add("is-active-day");
            else                             cell.classList.add("is-empty-day");

            const badge = info.is_sunday
                ? `<span class="admin-cell-badge">Closed</span>`
                : `<span class="admin-cell-badge">${info.total_booked} booked</span>`;

            cell.innerHTML = `
                <div class="flex-between">
                    <span class="admin-cell-number">${day}</span>
                    ${dateStr === todayStr ? '<span class="badge badge-teal" style="font-size:0.6rem;padding:1px 4px;">Today</span>' : ''}
                </div>
                <div>${badge}</div>`;

            cell.addEventListener("click", () => {
                selectedDate = dateStr;
                document.querySelectorAll(".admin-date-cell").forEach(c => c.classList.remove("is-selected-date"));
                cell.classList.add("is-selected-date");
                loadSelectedDateAppointments();
            });

            calGrid.appendChild(cell);
        }
    }

    // -------------------------------------------------------------------------
    // Appointments Panel
    // -------------------------------------------------------------------------
    async function loadSelectedDateAppointments() {
        const svc = serviceFilter.value;
        dateHeading.textContent = formatReadableDate(selectedDate);
        dateSub.textContent     = `Schedule for ${selectedDate}`;

        // Show loading state in panel
        apptContainer.innerHTML = `
            <div class="text-center py-8">
                <div class="spinner" style="border-top-color:#0d9488;width:22px;height:22px;"></div>
                <p class="text-xs text-muted mt-2">Loading appointments…</p>
            </div>`;
        countText.textContent = "Loading…";

        try {
            const url  = `/api/admin/appointments?date=${selectedDate}&service=${encodeURIComponent(svc)}`;
            const resp = await fetch(url);
            const data = await resp.json();

            if (resp.ok && data.success) {
                renderApptList(data.appointments || []);
            } else {
                apptContainer.innerHTML = `<div class="text-center py-6 text-rose-600 text-xs font-semibold">Failed: ${escapeHtml(data.message || "Error")}</div>`;
                countText.textContent = "Error loading.";
            }
        } catch {
            apptContainer.innerHTML = `<div class="text-center py-6 text-rose-600 text-xs font-semibold">Network error.</div>`;
            countText.textContent = "Error.";
        }
    }

    function renderApptList(appts) {
        countText.textContent = `Showing ${appts.length} appointment${appts.length === 1 ? "" : "s"}`;

        if (!appts.length) {
            apptContainer.innerHTML = `
                <div class="text-center py-12 glass-subtle p-6 rounded-md">
                    <div class="placeholder-icon mb-2" style="width:48px;height:48px;margin:0 auto;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/></svg>
                    </div>
                    <p class="text-sm font-bold text-slate-700">No appointments scheduled</p>
                    <p class="text-xs text-muted mt-1">No bookings match your criteria for this date.</p>
                </div>`;
            return;
        }

        apptContainer.innerHTML = "";

        appts.forEach(appt => {
            // Build full name from individual parts
            const fullName = appt.full_name || [appt.first_name, appt.middle_name, appt.last_name].filter(Boolean).join(" ");

            let badgeClass = "badge-blue";
            if (appt.status === "Completed") badgeClass = "badge-teal";
            if (appt.status === "Cancelled") badgeClass = "badge-rose";

            const card = document.createElement("div");
            card.className = "admin-appointment-card";
            card.innerHTML = `
                <div class="card-top-row">
                    <div>
                        <span class="patient-name-title">${escapeHtml(fullName)}</span>
                        <span class="patient-age-badge">(${appt.age} yrs old)</span>
                    </div>
                    <div class="flex-center gap-1">
                        <span class="badge badge-teal">${escapeHtml(appt.service)}</span>
                        <span class="badge ${badgeClass}">${escapeHtml(appt.status)}</span>
                    </div>
                </div>

                <div class="patient-detail-grid">
                    <span class="detail-label">1. Full Name:</span>
                    <span class="detail-value">${escapeHtml(fullName)}</span>

                    <span class="detail-label">2. Age:</span>
                    <span class="detail-value">${appt.age} years old</span>

                    <span class="detail-label">3. Schedule Date:</span>
                    <span class="detail-value font-semibold">${formatReadableDate(appt.appointment_date)}</span>

                    <span class="detail-label">4. Time Slot:</span>
                    <span class="detail-value font-semibold text-teal-800">${escapeHtml(appt.time_slot)}</span>

                    <span class="detail-label">5. Contact Number:</span>
                    <span class="detail-value"><a href="tel:${appt.contact_number}" class="text-teal-700 font-mono">${escapeHtml(appt.contact_number)}</a></span>

                    <span class="detail-label">6. Address:</span>
                    <span class="detail-value">${escapeHtml(appt.address)}</span>

                    <span class="detail-label">7. Province:</span>
                    <span class="detail-value">${escapeHtml(appt.province)}</span>

                    <span class="detail-label">8. City:</span>
                    <span class="detail-value">${escapeHtml(appt.city)}</span>
                </div>

                <div class="card-actions-row">
                    <span class="text-xs text-muted mr-auto font-mono" style="font-size:0.7rem;">Ref: ${escapeHtml(appt.reference_no)}</span>

                    ${appt.status !== "Completed" ? `
                        <button type="button" class="btn-complete-action" data-id="${appt.id}" data-name="${escapeHtml(fullName)}">
                            ✓ Mark Complete
                        </button>` : ""}

                    ${appt.status !== "Cancelled" ? `
                        <button type="button" class="btn-cancel-action" data-id="${appt.id}" data-name="${escapeHtml(fullName)}">
                            ✕ Cancel
                        </button>` : ""}
                </div>`;

            card.querySelector(".btn-complete-action")?.addEventListener("click", () =>
                openConfirm({ appointmentId: appt.id, newStatus: "Completed", patientName: fullName }));

            card.querySelector(".btn-cancel-action")?.addEventListener("click", () =>
                openConfirm({ appointmentId: appt.id, newStatus: "Cancelled", patientName: fullName }));

            apptContainer.appendChild(card);
        });
    }

    function openConfirm({ appointmentId, newStatus, patientName }) {
        pendingAction = { appointmentId, newStatus };

        if (newStatus === "Completed") {
            confirmTitle.textContent = "Mark as Completed?";
            confirmDesc.textContent  = `Mark the appointment for "${patientName}" as Completed?`;
            confirmIcon.innerHTML    = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
            confirmIcon.style.background = "rgba(20,184,166,0.15)";
            proceedBtn.textContent   = "Mark Completed";
            proceedBtn.style.background  = "";
        } else {
            confirmTitle.textContent = "Cancel Appointment?";
            confirmDesc.textContent  = `Cancel the booking for "${patientName}"? This frees up the slot.`;
            confirmIcon.innerHTML    = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
            confirmIcon.style.background = "rgba(244,63,94,0.15)";
            proceedBtn.textContent   = "Yes, Cancel Booking";
            proceedBtn.style.background  = "linear-gradient(135deg,#e11d48,#be123c)";
        }

        confirmModal.classList.remove("hidden");
    }

    proceedBtn.addEventListener("click", async () => {
        if (!pendingAction) return;
        const { appointmentId, newStatus } = pendingAction;
        proceedBtn.disabled     = true;
        proceedBtn.textContent  = "Updating…";

        try {
            const resp = await fetch(`/api/admin/appointments/${appointmentId}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body:   JSON.stringify({ status: newStatus })
            });
            const data = await resp.json();

            if (resp.ok && data.success) {
                showToast(`Status updated to '${newStatus}'.`, "success");
                confirmModal.classList.add("hidden");
                pendingAction = null;
                await loadSelectedDateAppointments();
                await loadAdminCalendar(adminYear, adminMonth);
            } else {
                showToast(data.message || "Failed to update.", "error");
            }
        } catch {
            showToast("Server error.", "error");
        } finally {
            proceedBtn.disabled    = false;
            proceedBtn.textContent = "Confirm";
        }
    });

    cancelModalBtn.addEventListener("click", () => {
        confirmModal.classList.add("hidden");
        pendingAction = null;
    });

    confirmModal.addEventListener("click", (e) => {
        if (e.target === confirmModal) { confirmModal.classList.add("hidden"); pendingAction = null; }
    });

    // Month nav
    prevBtn.addEventListener("click", () => {
        let m = adminMonth - 1, y = adminYear;
        if (m < 1) { m = 12; y--; }
        loadAdminCalendar(y, m);
    });

    nextBtn.addEventListener("click", () => {
        let m = adminMonth + 1, y = adminYear;
        if (m > 12) { m = 1; y++; }
        loadAdminCalendar(y, m);
    });

    todayBtn.addEventListener("click", () => {
        selectedDate = `${realDate.getFullYear()}-${String(realDate.getMonth()+1).padStart(2,"0")}-${String(realDate.getDate()).padStart(2,"0")}`;
        loadAdminCalendar(realYear, realMonth);
        loadSelectedDateAppointments();
    });

    serviceFilter.addEventListener("change", () => loadSelectedDateAppointments());

    // FIX: Refresh button — reloads both calendar AND panel with visible loading state
    refreshBtn.addEventListener("click", async () => {
        refreshBtn.textContent  = "⟳ Refreshing…";
        refreshBtn.disabled     = true;
        try {
            await Promise.all([
                loadAdminCalendar(adminYear, adminMonth),
                loadSelectedDateAppointments()
            ]);
            showToast("Dashboard refreshed.", "success");
        } finally {
            refreshBtn.textContent = "⟳ Refresh";
            refreshBtn.disabled    = false;
        }
    });

    // Initial load
    loadAdminCalendar(adminYear, adminMonth);
    loadSelectedDateAppointments();
}

// =============================================================================
// ADMIN HISTORY
// =============================================================================
function initAdminHistory() {
    const tableBody    = document.getElementById("history-table-body");
    const searchInput  = document.getElementById("history-search-input");
    const statusFilter = document.getElementById("history-status-filter");
    const refreshBtn   = document.getElementById("history-refresh-btn");
    const countText    = document.getElementById("history-count-text");
    const emptyState   = document.getElementById("history-empty-state");

    const confirmModal   = document.getElementById("status-confirm-modal");
    const confirmTitle   = document.getElementById("confirm-modal-title");
    const confirmDesc    = document.getElementById("confirm-modal-desc");
    const confirmIcon    = document.getElementById("confirm-modal-icon");
    const proceedBtn     = document.getElementById("confirm-modal-proceed-btn");
    const cancelModalBtn = document.getElementById("confirm-modal-cancel-btn");

    let pendingAction      = null;
    let debounceTimer      = null;

    async function fetchHistory() {
        const q   = searchInput.value.trim();
        const sts = statusFilter.value;
        countText.textContent = "Loading records…";

        try {
            const resp = await fetch(`/api/admin/history?search=${encodeURIComponent(q)}&status=${encodeURIComponent(sts)}`);
            const data = await resp.json();
            if (resp.ok && data.success) {
                renderTable(data.appointments || []);
            } else {
                tableBody.innerHTML = `<tr><td colspan="9" class="text-center py-6 text-rose-600">Failed: ${escapeHtml(data.message || "Error")}</td></tr>`;
            }
        } catch {
            tableBody.innerHTML = `<tr><td colspan="9" class="text-center py-6 text-rose-600">Network error.</td></tr>`;
        }
    }

    function renderTable(records) {
        countText.textContent = `Total Records: ${records.length}`;

        if (!records.length) {
            tableBody.innerHTML = "";
            emptyState.classList.remove("hidden");
            return;
        }

        emptyState.classList.add("hidden");
        tableBody.innerHTML = "";

        records.forEach(row => {
            const fullName = row.full_name || [row.first_name, row.middle_name, row.last_name].filter(Boolean).join(" ");

            let statusClass = "status-badge-booked";
            if (row.status === "Completed") statusClass = "status-badge-completed";
            if (row.status === "Cancelled") statusClass = "status-badge-cancelled";

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><code class="font-mono text-teal-800 font-bold">${escapeHtml(row.reference_no)}</code></td>
                <td>
                    <div class="font-bold text-slate-900">${escapeHtml(fullName)}</div>
                    <div class="text-xs text-muted">${escapeHtml(row.city)}, ${escapeHtml(row.province)}</div>
                </td>
                <td>${row.age}</td>
                <td class="font-semibold text-slate-800">${formatShortDate(row.appointment_date)}</td>
                <td class="text-xs font-medium">${escapeHtml(row.time_slot)}</td>
                <td><span class="badge badge-teal">${escapeHtml(row.service)}</span></td>
                <td><a href="tel:${row.contact_number}" class="text-teal-700 font-mono text-xs">${escapeHtml(row.contact_number)}</a></td>
                <td><span class="${statusClass}">${escapeHtml(row.status)}</span></td>
                <td class="text-right">
                    <div class="flex-center justify-end gap-1">
                        ${row.status === "Booked" ? `
                            <button type="button" class="btn-complete-action h-complete-btn" data-id="${row.id}" data-name="${escapeHtml(fullName)}">Complete</button>
                            <button type="button" class="btn-cancel-action h-cancel-btn"   data-id="${row.id}" data-name="${escapeHtml(fullName)}">Cancel</button>
                        ` : `<span class="text-xs text-muted">&mdash;</span>`}
                    </div>
                </td>`;

            tr.querySelector(".h-complete-btn")?.addEventListener("click", () =>
                openHistConfirm(row.id, "Completed", fullName));
            tr.querySelector(".h-cancel-btn")?.addEventListener("click",   () =>
                openHistConfirm(row.id, "Cancelled", fullName));

            tableBody.appendChild(tr);
        });
    }

    function openHistConfirm(id, newStatus, name) {
        pendingAction = { appointmentId: id, newStatus };

        if (newStatus === "Completed") {
            confirmTitle.textContent = "Mark as Completed?";
            confirmDesc.textContent  = `Mark "${name}" as Completed?`;
            confirmIcon.innerHTML    = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
            confirmIcon.style.background = "rgba(20,184,166,0.15)";
            proceedBtn.textContent   = "Mark Completed";
            proceedBtn.style.background  = "";
        } else {
            confirmTitle.textContent = "Cancel Appointment?";
            confirmDesc.textContent  = `Cancel the booking for "${name}"? The slot will be freed.`;
            confirmIcon.innerHTML    = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
            confirmIcon.style.background = "rgba(244,63,94,0.15)";
            proceedBtn.textContent   = "Yes, Cancel";
            proceedBtn.style.background  = "linear-gradient(135deg,#e11d48,#be123c)";
        }

        confirmModal.classList.remove("hidden");
    }

    proceedBtn.addEventListener("click", async () => {
        if (!pendingAction) return;
        const { appointmentId, newStatus } = pendingAction;
        proceedBtn.disabled    = true;
        proceedBtn.textContent = "Updating…";

        try {
            const resp = await fetch(`/api/admin/appointments/${appointmentId}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body:   JSON.stringify({ status: newStatus })
            });
            const data = await resp.json();

            if (resp.ok && data.success) {
                showToast(`Status updated to '${newStatus}'.`, "success");
                confirmModal.classList.add("hidden");
                pendingAction = null;
                await fetchHistory();
            } else {
                showToast(data.message || "Failed.", "error");
            }
        } catch {
            showToast("Server error.", "error");
        } finally {
            proceedBtn.disabled    = false;
            proceedBtn.textContent = "Confirm";
        }
    });

    cancelModalBtn.addEventListener("click", () => {
        confirmModal.classList.add("hidden");
        pendingAction = null;
    });

    confirmModal.addEventListener("click", (e) => {
        if (e.target === confirmModal) { confirmModal.classList.add("hidden"); pendingAction = null; }
    });

    searchInput.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(fetchHistory, 300);
    });

    statusFilter.addEventListener("change", fetchHistory);
    refreshBtn.addEventListener("click", fetchHistory);

    fetchHistory();
}
