"""Full End-to-End verification script against live running backend server (http://127.0.0.1:8000)."""

import httpx as requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_full_live_flow():
    print("==================================================")
    print("RUNNING LIVE END-TO-END NOTIFICATION SYSTEM TESTS")
    print("==================================================")

    # 1. Health check
    res = requests.get(f"{BASE_URL}/api/v1/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Backend health check OK")

    # 2. Login as Caregiver
    cg_login = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "caregiver@pillsync.com",
        "password": "Password123!"
    })
    assert cg_login.status_code == 200, f"Caregiver login failed: {cg_login.text}"
    cg_token = cg_login.json()["access_token"]
    cg_user = cg_login.json()["user"]
    cg_headers = {"Authorization": f"Bearer {cg_token}"}
    print(f"[PASS] Caregiver authenticated: {cg_user['name']} ({cg_user['role']})")

    # 3. Caregiver Dashboard & Alerts
    cg_dash = requests.get(f"{BASE_URL}/api/v1/caregiver/dashboard", headers=cg_headers)
    assert cg_dash.status_code == 200, f"Caregiver dashboard failed: {cg_dash.text}"
    dash_data = cg_dash.json()
    assert dash_data["total_assigned_patients"] >= 1
    print(f"[PASS] Caregiver assigned patients: {dash_data['total_assigned_patients']}, Scheduled doses: {dash_data['today_doses_scheduled']}")

    cg_alerts = requests.get(f"{BASE_URL}/api/v1/caregiver/alerts", headers=cg_headers)
    assert cg_alerts.status_code == 200, f"Caregiver alerts failed: {cg_alerts.text}"
    alerts_data = cg_alerts.json()
    assert len(alerts_data) > 0, "Caregiver should have active alerts"
    print(f"[PASS] Caregiver active alerts count: {len(alerts_data)}")
    for a in alerts_data:
        print(f"       - [{a['type']}] {a['title']} | Patient: {a['patient_name']} | Severity: {a['severity']}")

    # 4. Login as Patient
    pt_login = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "patient@pillsync.com",
        "password": "Password123!"
    })
    assert pt_login.status_code == 200, f"Patient login failed: {pt_login.text}"
    pt_token = pt_login.json()["access_token"]
    pt_user = pt_login.json()["user"]
    pt_headers = {"Authorization": f"Bearer {pt_token}"}
    print(f"[PASS] Patient authenticated: {pt_user['name']} ({pt_user['role']})")

    # 5. Patient Notifications & Unread Count
    pt_notifs = requests.get(f"{BASE_URL}/api/v1/patient/notifications", headers=pt_headers)
    assert pt_notifs.status_code == 200, f"Patient notifications failed: {pt_notifs.text}"
    notifs_data = pt_notifs.json()
    assert len(notifs_data) > 0, "Patient should have real notifications"
    print(f"[PASS] Patient notifications count: {len(notifs_data)}")
    for n in notifs_data:
        print(f"       - [{n['type']}] {n['title']} | Medicine: {n['medicine_name']} | Read: {n['is_read']}")

    pt_unread = requests.get(f"{BASE_URL}/api/v1/patient/notifications/unread-count", headers=pt_headers)
    assert pt_unread.status_code == 200
    unread_count = pt_unread.json()["unread_count"]
    print(f"[PASS] Patient active unread count: {unread_count}")

    # 6. Mark single notification as read
    unread_notifs = [n for n in notifs_data if not n["is_read"]]
    if unread_notifs:
        target_notif = unread_notifs[0]
        read_res = requests.post(f"{BASE_URL}/api/v1/patient/notifications/{target_notif['id']}/read", headers=pt_headers)
        assert read_res.status_code == 200
        print(f"[PASS] Marked notification {target_notif['id']} as read")

        # Verify unread count decremented
        pt_unread_after = requests.get(f"{BASE_URL}/api/v1/patient/notifications/unread-count", headers=pt_headers).json()["unread_count"]
        assert pt_unread_after == max(0, unread_count - 1)
        print(f"[PASS] Verified unread count decremented to {pt_unread_after}")

    # 7. Chat Messaging Flow: Patient sends message to Caregiver
    chat_send = requests.post(f"{BASE_URL}/api/v1/chat/send", headers=pt_headers, json={
        "recipient_id": cg_user["id"],
        "message": "Testing real-time live notification delivery."
    })
    assert chat_send.status_code == 201, f"Chat send failed: {chat_send.text}"
    print("[PASS] Patient sent live chat message to Caregiver")

    # Caregiver retrieves alerts and sees the chat notification
    cg_alerts_after = requests.get(f"{BASE_URL}/api/v1/caregiver/alerts", headers=cg_headers).json()
    chat_alert = next((a for a in cg_alerts_after if a["type"] == "CHAT_MESSAGE"), None)
    assert chat_alert is not None, "Caregiver must receive live chat alert"
    print(f"[PASS] Caregiver received live chat alert: '{chat_alert['title']}' - {chat_alert['message']}")

    # Caregiver opens conversation with Patient -> automatically marks messages as read
    cg_convo = requests.get(f"{BASE_URL}/api/v1/chat/conversation/{pt_user['id']}", headers=cg_headers)
    assert cg_convo.status_code == 200
    print(f"[PASS] Caregiver opened conversation ({len(cg_convo.json())} messages), messages marked read")

    # Verify chat alert resolved from caregiver alerts
    cg_alerts_resolved = requests.get(f"{BASE_URL}/api/v1/caregiver/alerts", headers=cg_headers).json()
    assert not any(a["id"] == chat_alert["id"] for a in cg_alerts_resolved)
    print("[PASS] Chat alert automatically cleared from caregiver notifications")

    # Caregiver replies to Patient
    cg_reply = requests.post(f"{BASE_URL}/api/v1/chat/send", headers=cg_headers, json={
        "recipient_id": pt_user["id"],
        "message": "Acknowledged. Updating your regimen."
    })
    assert cg_reply.status_code == 201
    print("[PASS] Caregiver replied to Patient successfully")

    # 8. Mark all patient notifications as read
    mark_all = requests.post(f"{BASE_URL}/api/v1/patient/notifications/read-all", headers=pt_headers)
    assert mark_all.status_code == 200
    final_unread = requests.get(f"{BASE_URL}/api/v1/patient/notifications/unread-count", headers=pt_headers).json()["unread_count"]
    assert final_unread == 0
    print("[PASS] Mark all read completed: unread count is 0")

    # 9. RBAC Boundaries
    unauth = requests.get(f"{BASE_URL}/api/v1/caregiver/alerts")
    assert unauth.status_code == 401
    print("[PASS] Unauthenticated access properly rejected with 401")

    forbidden = requests.get(f"{BASE_URL}/api/v1/caregiver/alerts", headers=pt_headers)
    assert forbidden.status_code == 403
    print("[PASS] Patient accessing caregiver endpoints rejected with 403")

    print("==================================================")
    print("ALL LIVE END-TO-END VERIFICATION CHECKS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_full_live_flow()
