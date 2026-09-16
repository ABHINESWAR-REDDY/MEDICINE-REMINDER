# PillSync Backend API Live Demonstration Guide (Mentor Presentation)

This document provides a step-by-step sequence for presenting the **PillSync FastAPI Backend** and PostgreSQL database in real-time to your mentor using **FastAPI Swagger UI (`/docs`)**.

---

## Pre-Requisites & Environment

- **RDBMS Engine**: PostgreSQL 16 (on `localhost:5432`, database: `myproject`)
- **Backend Server**: FastAPI on `http://127.0.0.1:8000`
- **Swagger Documentation URL**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation URL**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON URL**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## Presentation Walkthrough Sequence

### STEP 1: Start the Backend Server

Open a PowerShell terminal in the project root:

```powershell
cd C:\Users\admin\Desktop\pillsync\backend
..\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

*Expected output*: `Application startup complete. Uvicorn running on http://0.0.0.0:8000`

---

### STEP 2: Open Swagger UI

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

Show your mentor:
- The **API Title, Description, and Metadata**.
- The **14 Tagged Endpoint Categories** (Health, Authentication, Patient Doses & Adherence, Patient Notifications, Caregivers, Admin, Medicines, Schedules, Chat, OCR, etc.).
- Total of **69 live endpoints**.

---

### STEP 3: Demonstrate Live Health & Database Connectivity

1. Expand the **`Health`** tag.
2. Click on **`GET /api/v1/health`** $\rightarrow$ **Try it out** $\rightarrow$ **Execute**.
3. Point out to your mentor that the database is checked in real-time against PostgreSQL:
   ```json
   {
     "status": "healthy",
     "environment": "development",
     "version": "0.1.0",
     "timestamp": "2026-08-25T16:05:15.123456Z",
     "services": {
       "api": {
         "status": "healthy",
         "details": "API process operational"
       },
       "database": {
         "status": "healthy",
         "details": "connected"
       }
     }
   }
   ```

---

### STEP 4: Authenticate with a Real Account

1. Expand the **`Authentication`** tag.
2. Click on **`POST /api/v1/auth/login`** $\rightarrow$ **Try it out**.
3. Choose one of the real registered accounts in the database:
   - **Admin Account**: `abhineswar2312@gmail.com`
   - **Patient Account**: `koppalanaveen20@gmail.com` or `ksivachaithanyareddy@gmail.com`
   - **Caregiver Account**: `adityachowdary3007@gmail.com`
4. Enter the email and password, then click **Execute**.

---

### STEP 5: Copy the JWT Access Token

In the `200 OK` response body, copy the string value of **`access_token`**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 17,
    "employee_id": "AD000017",
    "name": "ADMINISTRATION",
    "email": "abhineswar2312@gmail.com",
    "role": "ADMIN",
    "approval_status": "APPROVED",
    "is_active": true
  }
}
```

---

### STEP 6 & 7: Authorize Swagger UI

1. Scroll to the top of the Swagger page and click the green **Authorize 🔓** button.
2. Under **`http_bearer (http, Bearer)`**, paste the copied JWT token into the **Value** input field.
3. Click **Authorize**, then click **Close**.
4. All secured endpoints will now display a closed padlock 🔒 and automatically inject `Authorization: Bearer <token>`.

---

### STEP 8: Demonstrate Patient APIs

*(Login with a Patient account, e.g. `koppalanaveen20@gmail.com` or authorize as patient)*

1. **`GET /api/v1/patient/dashboard`**: Returns summary metrics (total medications, today's pending doses, adherence rate).
2. **`GET /api/v1/medicines`**: Lists real active medications assigned to the patient.
3. **`GET /api/v1/schedules`**: Lists daily schedule frequencies and dose timing slots.
4. **`GET /api/v1/patient/doses`**: Lists all pending, taken, and scheduled doses.
5. **`GET /api/v1/patient/adherence?days=30`**: Calculates exact mathematical adherence percentage from database records.
6. **`GET /api/v1/patient/refill-predictions`**: Computes remaining doses, daily burn rate, and days until refill.
7. **`GET /api/v1/patient/notifications`**: Lists medication alarms and adherence warnings.

---

### STEP 9: Demonstrate Caregiver APIs

*(Authorize using a Caregiver account, e.g. `adityachowdary3007@gmail.com`)*

1. **`GET /api/v1/caregiver/dashboard`**: Displays aggregate statistics across all patients assigned to this caregiver.
2. **`GET /api/v1/caregiver/patients`**: Lists the caregiver's assigned patients with their compliance status.
3. **`GET /api/v1/caregiver/patients/{id}`**: Shows clinical profile, diagnosis, and active prescription details.
4. **`GET /api/v1/caregiver/adherence-reports`**: Retrieves 7-day and 30-day adherence percentages per assigned patient.
5. **`GET /api/v1/caregiver/alerts`**: Lists actionable alerts for missed doses and urgent refill needs.

---

### STEP 10: Demonstrate Admin APIs

*(Authorize using the Admin account `abhineswar2312@gmail.com`)*

1. **`GET /api/v1/admin/dashboard`**: Overall platform statistics (total users, active patients, approved caregivers, system health).
2. **`GET /api/v1/admin/caregivers`**: Lists all registered caregivers with filtering by approval status (`PENDING`, `APPROVED`, `REJECTED`).
3. **`GET /api/v1/admin/patient-assignments`**: Shows relational links between caregivers and patients.
4. **`GET /api/v1/admin/audit-logs`**: Shows immutable system audit logs recording registration events, approvals, and logins.
5. **`GET /api/v1/admin/platform-activities`**: Displays real-time database-driven user activities.
6. **`GET /api/v1/admin/analytics`**: Dynamic adherence distribution across the entire platform.

---

### STEP 11: Demonstrate Role-Based Access Control (RBAC) Enforcement

Show your mentor that the system strictly prevents privilege escalation:

1. With a **PATIENT** token active in Swagger:
   - Try to execute **`GET /api/v1/admin/dashboard`** or **`GET /api/v1/admin/caregivers`**.
   - **Result**: Immediate **`HTTP 403 Forbidden`** with detail `"Insufficient permissions to access this resource."`.
2. With a **CAREGIVER** token active in Swagger:
   - Try to execute **`GET /api/v1/admin/audit-logs`**.
   - **Result**: **`HTTP 403 Forbidden`**.
3. With **NO** token or an invalid token:
   - Try to execute **`GET /api/v1/auth/me`**.
   - **Result**: **`HTTP 401 Unauthorized`**.

---

### STEP 12: Demonstrate a Live Database-Backed Workflow

Demonstrate an end-to-end dose completion flow with live PostgreSQL persistence:

1. Under **`Patient Doses & Adherence`**, execute **`GET /api/v1/patient/doses`**. Note the `id` of a `PENDING` dose (e.g. Dose ID `1`).
2. Execute **`POST /api/v1/patient/doses/{id}/take`** with that `id`.
   - Response: `200 OK` with `"status": "TAKEN"`, `"actual_time": "<timestamp>"`.
3. Execute **`GET /api/v1/patient/adherence?days=7`**:
   - Show how the calculated adherence score dynamically updates.
4. Open **pgAdmin 4** $\rightarrow$ `myproject` $\rightarrow$ `medication_doses`:
   - View all rows and point out that the dose record in PostgreSQL has updated `status = 'TAKEN'` and `actual_time`.

---

## Registered Endpoint Inventory (69 Routes)

| Tag | Category | Endpoints Count | Key Features |
| :--- | :--- | :--- | :--- |
| `Health` | Diagnostics | 1 | Live PostgreSQL DB connectivity check |
| `Authentication` | Auth & Security | 9 | Register, OTP email verify, login, forgot password, check employee ID |
| `Profile` | User Management | 1 | Safe profile retrieval with assigned caregiver info |
| `Patient Doses & Adherence` | Patient Care | 3 | Dose listing, mark taken, mark skipped, adherence stats |
| `Patient Notifications & Alerts` | Reminders | 4 | Notification feeds, unread badge count, mark single/all read |
| `Patient Portal History & Refills` | Patient Portal | 4 | Patient dashboard, dose logs, refill analytics, inventory |
| `Caregiver` | Supervision | 6 | Caregiver dashboard, assigned patients, adherence reports, alerts |
| `Admin` | Administration | 15 | Approvals, assignments, audit logs, activities, analytics, settings |
| `Medicines` | Pharmacy | 6 | CRUD medicines, reference medicine autocomplete (50,000 DB items) |
| `Schedules` | Timing | 5 | CRUD dosage schedules and daily frequency intervals |
| `Prescriptions` | Clinical | 5 | Prescription records, doctor names, notes, active status |
| `Conditions` | Diagnostics | 5 | Chronic illness categorizations |
| `Chat Messaging` | Real-time Comms | 5 | Contacts, message threads, send, mark read, soft delete |
| `OCR Prescriptions` | AI / ML Pipeline | 5 | Upload prescription scan, job polling, TrOCR inference, confirm digitize |
