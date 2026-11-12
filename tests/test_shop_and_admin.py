"""Comprehensive Unit & Integration Tests for Shop Profile, Wizard, and Admin Portal."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.db import Shop, ShopOwner, create_db_and_tables, get_session
from app.main import app
from app.security import hash_password

from tests.conftest import shared_engine as test_engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure admin exists before tests."""
    with Session(test_engine) as session:
        admin = session.exec(select(ShopOwner).where(ShopOwner.email == "admin@voicekhata.com")).first()
        if not admin:
            admin = ShopOwner(
                full_name="Admin User",
                email="admin@voicekhata.com",
                mobile_number="+919999999999",
                password_hash=hash_password("Admin@123456"),
                role="admin",
                email_verified=True,
                phone_verified=True,
                account_status="active",
            )
            session.add(admin)
            session.commit()


_owner_counter = 0

def create_and_login_owner(tag=None):
    """Helper to create and login a standard shop owner with unique credentials."""
    global _owner_counter
    _owner_counter += 1
    tag = tag or f"user{_owner_counter}"
    email = f"owner_{tag}@example.com"
    mobile = f"+9198{_owner_counter:08d}"
    client.post("/api/auth/register", json={
        "full_name": f"Owner {tag}",
        "email": email,
        "mobile_number": mobile,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True,
    })
    login_resp = client.post("/api/auth/login", json={
        "identifier": email,
        "password": "Password123!",
    })
    token = login_resp.json()["token"]
    return token, email


# ---------------------------------------------------------------------------
# Wizard & Shop Profile Tests
# ---------------------------------------------------------------------------

def test_wizard_step_progress_saving():
    token, _ = create_and_login_owner()
    headers = {"Authorization": f"Bearer {token}"}

    # Save Step 1
    resp1 = client.post("/api/shop-owner/wizard/step", json={
        "step": 1,
        "data": {},
    }, headers=headers)
    assert resp1.status_code == 200

    # Save Step 2 (Shop Info)
    resp2 = client.post("/api/shop-owner/wizard/step", json={
        "step": 2,
        "data": {
            "shop_name": "Gupta Kirana Store",
            "shop_category": "Grocery Store",
            "shop_mobile_number": "+919877788899",
            "opening_time": "08:00 AM",
            "closing_time": "10:00 PM",
            "weekly_closing_day": "Tuesday",
        },
    }, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["registration_step"] == 2

    # Save Step 3 (Address & Location)
    resp3 = client.post("/api/shop-owner/wizard/step", json={
        "step": 3,
        "data": {
            "street": "MG Road",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "pincode": "452001",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "complete_address": "12, MG Road, Indore, MP 452001",
        },
    }, headers=headers)
    assert resp3.status_code == 200
    assert resp3.json()["registration_step"] == 3

    # Check status
    status_resp = client.get("/api/shop-owner/status", headers=headers)
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["registration_step"] == 3
    assert not data["is_registration_complete"]


def test_wizard_complete():
    token, _ = create_and_login_owner()
    headers = {"Authorization": f"Bearer {token}"}

    complete_payload = {
        "shop_name": "Gupta Kirana Store",
        "shop_category": "Grocery Store",
        "shop_description": "Fresh groceries and dairy daily",
        "shop_mobile_number": "+919877788899",
        "opening_time": "08:00 AM",
        "closing_time": "10:00 PM",
        "weekly_closing_day": "None",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "pincode": "452001",
        "complete_address": "Shop 4, Market Complex, MG Road, Indore",
        "latitude": 22.7196,
        "longitude": 75.8577,
    }

    resp = client.post("/api/shop-owner/wizard/complete", json=complete_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["shop"]["is_registration_complete"] is True
    assert "google_maps_url" in data["shop"]

    # Verify Shop details endpoint
    shop_resp = client.get("/api/shop-owner/shop", headers=headers)
    assert shop_resp.status_code == 200
    assert shop_resp.json()["shop_name"] == "Gupta Kirana Store"
    assert shop_resp.json()["city"] == "Indore"


def test_update_shop_and_profile():
    token, _ = create_and_login_owner()
    headers = {"Authorization": f"Bearer {token}"}

    # Complete wizard first
    client.post("/api/shop-owner/wizard/complete", json={
        "shop_name": "Gupta General Store",
        "shop_category": "Grocery Store",
        "shop_mobile_number": "+919877788899",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "pincode": "452001",
        "complete_address": "Indore Market",
    }, headers=headers)

    # Update shop name and timings
    update_shop = client.put("/api/shop-owner/shop", json={
        "shop_name": "Gupta Supermart",
        "closing_time": "11:00 PM",
    }, headers=headers)
    assert update_shop.status_code == 200
    assert update_shop.json()["shop"]["shop_name"] == "Gupta Supermart"

    # Update owner profile name
    update_prof = client.put("/api/shop-owner/profile", json={
        "full_name": "Ravi Kumar Gupta",
    }, headers=headers)
    assert update_prof.status_code == 200
    assert update_prof.json()["owner"]["full_name"] == "Ravi Kumar Gupta"


def test_change_password_and_sessions():
    token, _ = create_and_login_owner()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Change password with incorrect current password
    bad_change = client.post("/api/shop-owner/change-password", json={
        "current_password": "WrongPassword",
        "new_password": "BrandNewPass123!",
        "confirm_password": "BrandNewPass123!",
    }, headers=headers)
    assert bad_change.status_code == 400

    # 2. Change password with correct current password
    good_change = client.post("/api/shop-owner/change-password", json={
        "current_password": "Password123!",
        "new_password": "BrandNewPass123!",
        "confirm_password": "BrandNewPass123!",
    }, headers=headers)
    assert good_change.status_code == 200

    # 3. List active sessions
    sessions_resp = client.get("/api/shop-owner/sessions", headers=headers)
    assert sessions_resp.status_code == 200
    sessions_list = sessions_resp.json()
    assert len(sessions_list) >= 1
    session_id = sessions_list[0]["id"]

    # 4. Terminate session
    term_resp = client.delete(f"/api/shop-owner/sessions/{session_id}", headers=headers)
    assert term_resp.status_code == 200


# ---------------------------------------------------------------------------
# Admin Portal & Role-Based Access Control Tests
# ---------------------------------------------------------------------------

def test_admin_portal_flow_and_rbac():
    # 1. Non-admin user tries to access admin endpoint -> 403 Forbidden
    owner_token, _ = create_and_login_owner()
    non_admin_resp = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {owner_token}"})
    assert non_admin_resp.status_code == 403

    # 2. Admin logs in
    admin_login = client.post("/api/admin/login", json={
        "email": "admin@voicekhata.com",
        "password": "Admin@123456",
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Admin gets stats
    stats_resp = client.get("/api/admin/stats", headers=admin_headers)
    assert stats_resp.status_code == 200
    assert stats_resp.json()["total_shop_owners"] >= 1

    # 4. Admin lists shop owners
    owners_resp = client.get("/api/admin/shop-owners", headers=admin_headers)
    assert owners_resp.status_code == 200
    owners = owners_resp.json()
    assert len(owners) >= 1
    target_owner_id = owners[0]["id"]

    # 5. Admin searches shop owners by query
    search_resp = client.get("/api/admin/shop-owners?q=owner", headers=admin_headers)
    assert search_resp.status_code == 200
    assert len(search_resp.json()) >= 1

    # 6. Admin updates owner status to suspended
    suspend_resp = client.put(f"/api/admin/shop-owners/{target_owner_id}/status", json={
        "account_status": "suspended",
    }, headers=admin_headers)
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["new_status"] == "suspended"

    # Suspended owner cannot access shop profile
    blocked_resp = client.get("/api/shop-owner/profile", headers={"Authorization": f"Bearer {owner_token}"})
    assert blocked_resp.status_code in (401, 403)

    # 7. Admin reactivates owner
    reactivate_resp = client.put(f"/api/admin/shop-owners/{target_owner_id}/status", json={
        "account_status": "active",
    }, headers=admin_headers)
    assert reactivate_resp.status_code == 200

    # 8. Admin views audit logs
    audit_resp = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    assert isinstance(audit_resp.json(), list)

