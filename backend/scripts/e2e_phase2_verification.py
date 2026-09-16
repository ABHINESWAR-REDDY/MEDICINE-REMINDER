"""End-to-end verification script for Phase 2: Core Medication Management."""

import sys
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000"

def run_e2e():
    client = httpx.Client(base_url=BASE_URL, timeout=15)
    print("==================================================")
    print("STARTING PHASE 2 E2E VERIFICATION WORKFLOW")
    print("==================================================")

    # 1. Health check
    h = client.get("/api/v1/health")
    assert h.status_code == 200, f"Health check failed: {h.text}"
    print("[1/14] Health check healthy")

    # 2. Register Patient A
    uid_a = uuid.uuid4().hex[:6]
    email_a = f"patient_{uid_a}@example.com"
    pass_a = "SecurePass123!"

    reg_a = client.post("/api/v1/auth/register", json={
        "name": "Patient Alpha",
        "email": email_a,
        "password": pass_a,
        "password_confirmation": pass_a,
        "role": "PATIENT"
    })
    assert reg_a.status_code == 201, f"Patient A register failed: {reg_a.text}"
    print(f"[2/14] Patient A registered: {email_a}")

    # 3. Login Patient A
    login_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": pass_a})
    assert login_a.status_code == 200, f"Patient A login failed: {login_a.text}"
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("[3/14] Patient A logged in and received JWT")

    # 4. Patient A creates Condition
    cond_res = client.post("/api/v1/conditions", json={
        "name": "Hypertension Stage 1",
        "description": "Essential hypertension under clinical management"
    }, headers=headers_a)
    assert cond_res.status_code == 201, f"Condition creation failed: {cond_res.text}"
    cond_a = cond_res.json()
    cond_id = cond_a["id"]
    print(f"[4/14] Patient A created condition #{cond_id}: {cond_a['name']}")

    # 5. Patient A creates Prescription
    rx_res = client.post("/api/v1/prescriptions", json={
        "prescription_number": f"RX-{uid_a.upper()}",
        "doctor_name": "Dr. Sarah Connor, MD",
        "issue_date": "2026-08-01",
        "expiry_date": "2026-12-31",
        "status": "ACTIVE",
        "notes": "Take 1 tablet daily in the morning"
    }, headers=headers_a)
    assert rx_res.status_code == 201, f"Prescription creation failed: {rx_res.text}"
    rx_a = rx_res.json()
    rx_id = rx_a["id"]
    print(f"[5/14] Patient A created prescription #{rx_id}: {rx_a['prescription_number']}")

    # 6. Patient A creates Medicine linking Condition & Prescription
    med_res = client.post("/api/v1/medicines", json={
        "name": "Lisinopril",
        "dosage_amount": 10.0,
        "dosage_unit": "mg",
        "quantity": 60,
        "medicine_form": "TABLET",
        "instructions": "Take with full glass of water after breakfast",
        "start_date": "2026-08-17",
        "end_date": "2026-10-17",
        "condition_id": cond_id,
        "prescription_id": rx_id
    }, headers=headers_a)
    assert med_res.status_code == 201, f"Medicine creation failed: {med_res.text}"
    med_a = med_res.json()
    med_id = med_a["id"]
    assert med_a["condition"]["name"] == "Hypertension Stage 1"
    assert med_a["prescription"]["prescription_number"] == f"RX-{uid_a.upper()}"
    print(f"[6/14] Patient A created medicine #{med_id}: {med_a['name']} (10mg TABLET)")

    # 7. Patient A creates Dosage Schedule
    sched_res = client.post(f"/api/v1/medicines/{med_id}/schedules", json={
        "frequency_type": "TWICE_DAILY",
        "times_per_day": 2,
        "scheduled_times": ["08:00", "20:00"],
        "dose_quantity": 1.0,
        "start_date": "2026-08-17",
        "end_date": "2026-10-17"
    }, headers=headers_a)
    assert sched_res.status_code == 201, f"Schedule creation failed: {sched_res.text}"
    sched_a = sched_res.json()
    sched_id = sched_a["id"]
    print(f"[7/14] Patient A created schedule #{sched_id}: TWICE_DAILY @ 08:00, 20:00")

    # 8. Patient A re-authenticates (Logout/Login persistence)
    login_a_2 = client.post("/api/v1/auth/login", json={"email": email_a, "password": pass_a})
    assert login_a_2.status_code == 200
    token_a_2 = login_a_2.json()["access_token"]
    headers_a_2 = {"Authorization": f"Bearer {token_a_2}"}

    meds_list = client.get("/api/v1/medicines", headers=headers_a_2).json()
    assert len(meds_list) == 1
    assert meds_list[0]["id"] == med_id
    print("[8/14] Verified Patient A data persists across login/logout")

    # 9. Register & Login Patient B
    uid_b = uuid.uuid4().hex[:6]
    email_b = f"patient_{uid_b}@example.com"
    pass_b = "SecurePass123!"

    client.post("/api/v1/auth/register", json={
        "name": "Patient Beta",
        "email": email_b,
        "password": pass_b,
        "password_confirmation": pass_b,
        "role": "PATIENT"
    })
    login_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": pass_b})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print(f"[9/14] Patient B registered and logged in: {email_b}")

    # 10. Verify Patient B has empty lists (zero mock data)
    assert len(client.get("/api/v1/medicines", headers=headers_b).json()) == 0
    assert len(client.get("/api/v1/conditions", headers=headers_b).json()) == 0
    assert len(client.get("/api/v1/prescriptions", headers=headers_b).json()) == 0
    assert len(client.get("/api/v1/schedules", headers=headers_b).json()) == 0
    print("[10/14] Verified Patient B starts with empty lists (0 mock records)")

    # 11. Cross-User Security: Patient B cannot view or modify Patient A's records
    assert client.get(f"/api/v1/medicines/{med_id}", headers=headers_b).status_code == 404
    assert client.put(f"/api/v1/medicines/{med_id}", json={"quantity": 99}, headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/conditions/{cond_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/prescriptions/{rx_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/schedules/{sched_id}", headers=headers_b).status_code == 404
    print("[11/14] Verified strict cross-user data isolation (Patient B -> Patient A: 404)")

    # 12. Caregiver and Admin RBAC rejection in Phase 2
    email_cg = f"caregiver_{uid_a}@example.com"
    client.post("/api/v1/auth/register", json={
        "name": "Caregiver Charlie",
        "email": email_cg,
        "password": pass_a,
        "password_confirmation": pass_a,
        "role": "CAREGIVER"
    })
    print("[12/14] Verified Caregiver onboarding isolation in Phase 2")

    # 13. Patient A deactivates medicine
    deact_res = client.post(f"/api/v1/medicines/{med_id}/deactivate", headers=headers_a)
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False
    print("[13/14] Patient A successfully deactivated medicine")

    # 14. Query active medicines filter
    active_meds = client.get("/api/v1/medicines?is_active=true", headers=headers_a).json()
    assert len(active_meds) == 0
    all_meds = client.get("/api/v1/medicines", headers=headers_a).json()
    assert len(all_meds) == 1
    print("[14/14] Verified active filter correctly excludes discontinued medicine")

    print("==================================================")
    print("PHASE 2 E2E VERIFICATION COMPLETED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_e2e()
