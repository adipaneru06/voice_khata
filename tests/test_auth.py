"""Comprehensive Unit & Integration Tests for Shop Owner Authentication & OTP."""

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
def clean_auth_tables():
    """Ensure auth tables have default admin before each test in this module."""
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


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------

def test_register_success():
    payload = {
        "full_name": "Ramesh Kumar",
        "email": "ramesh@example.com",
        "mobile_number": "+919876543210",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True,
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["email"] == "ramesh@example.com"
    assert "dev_otp" in data or "next_step" in data

    # Verify user created in DB
    with Session(test_engine) as s:
        user = s.exec(select(ShopOwner).where(ShopOwner.email == "ramesh@example.com")).first()
        assert user is not None
        assert user.full_name == "Ramesh Kumar"
        assert not user.email_verified


def test_register_duplicate_email():
    payload = {
        "full_name": "Ramesh Kumar",
        "email": "ramesh@example.com",
        "mobile_number": "+919876543210",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True,
    }
    client.post("/api/auth/register", json=payload)
    # Attempt duplicate email
    payload2 = {
        "full_name": "Another Ramesh",
        "email": "ramesh@example.com",
        "mobile_number": "+919876543211",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True,
    }
    resp2 = client.post("/api/auth/register", json=payload2)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


def test_register_duplicate_phone():
    payload = {
        "full_name": "Ramesh Kumar",
        "email": "ramesh1@example.com",
        "mobile_number": "+919876543210",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True,
    }
    client.post("/api/auth/register", json=payload)
    # Attempt duplicate phone with different email
    payload2 = {
        "full_name": "Suresh Kumar",
        "email": "suresh@example.com",
        "mobile_number": "+919876543210",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True,
    }
    resp2 = client.post("/api/auth/register", json=payload2)
    assert resp2.status_code == 409
    assert "mobile number is already registered" in resp2.json()["detail"].lower() or "already exists" in resp2.json()["detail"].lower()


def test_register_password_mismatch_and_weak():
    payload = {
        "full_name": "Ramesh Kumar",
        "email": "ramesh@example.com",
        "mobile_number": "+919876543210",
        "password": "pass",
        "confirm_password": "different",
        "terms_accepted": True,
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 400
    assert "passwords do not match" in resp.json()["detail"].lower()

    # Weak password
    payload["confirm_password"] = "pass"
    resp2 = client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "at least 8 characters" in resp2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Login Tests
# ---------------------------------------------------------------------------

def test_login_with_email_and_phone():
    # Register user
    reg_payload = {
        "full_name": "Priya Sharma",
        "email": "priya@example.com",
        "mobile_number": "+919123456789",
        "password": "MySecretPass123!",
        "confirm_password": "MySecretPass123!",
        "terms_accepted": True,
    }
    client.post("/api/auth/register", json=reg_payload)

    # 1. Login with email
    resp1 = client.post("/api/auth/login", json={
        "identifier": "priya@example.com",
        "password": "MySecretPass123!",
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "token" in data1
    assert data1["owner"]["full_name"] == "Priya Sharma"

    # 2. Login with phone number
    resp2 = client.post("/api/auth/login", json={
        "identifier": "+919123456789",
        "password": "MySecretPass123!",
    })
    assert resp2.status_code == 200
    assert "token" in resp2.json()

    # 3. Login with wrong password
    resp3 = client.post("/api/auth/login", json={
        "identifier": "priya@example.com",
        "password": "WrongPassword!",
    })
    assert resp3.status_code == 401


# ---------------------------------------------------------------------------
# OTP Verification Tests
# ---------------------------------------------------------------------------

def test_otp_flow():
    # Register user
    reg_payload = {
        "full_name": "Mohan Lal",
        "email": "mohan@example.com",
        "mobile_number": "+919811122233",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True,
    }
    reg_resp = client.post("/api/auth/register", json=reg_payload)
    dev_otp = reg_resp.json().get("dev_otp")

    # Verify email OTP
    verify_resp = client.post("/api/otp/verify-email", json={
        "target": "mohan@example.com",
        "otp_code": dev_otp,
    })
    assert verify_resp.status_code == 200
    assert verify_resp.json()["email_verified"] is True

    # Send phone OTP
    phone_otp_resp = client.post("/api/otp/send-phone", json={
        "target": "+919811122233",
        "otp_type": "phone",
    })
    assert phone_otp_resp.status_code == 200
    phone_dev_otp = phone_otp_resp.json().get("dev_otp")

    # Test invalid OTP code
    bad_verify = client.post("/api/otp/verify-phone", json={
        "target": "+919811122233",
        "otp_code": "000000",
    })
    assert bad_verify.status_code == 400
    assert "incorrect" in bad_verify.json()["detail"].lower()

    # Verify phone OTP with valid code
    good_verify = client.post("/api/otp/verify-phone", json={
        "target": "+919811122233",
        "otp_code": phone_dev_otp,
    })
    assert good_verify.status_code == 200
    assert good_verify.json()["phone_verified"] is True


# ---------------------------------------------------------------------------
# Forgot & Reset Password Tests
# ---------------------------------------------------------------------------

def test_forgot_and_reset_password():
    reg_payload = {
        "full_name": "Sunil Verma",
        "email": "sunil@example.com",
        "mobile_number": "+919844455566",
        "password": "OldPassword123!",
        "confirm_password": "OldPassword123!",
        "terms_accepted": True,
    }
    client.post("/api/auth/register", json=reg_payload)

    # Request forgot password
    forgot_resp = client.post("/api/auth/forgot-password", json={
        "identifier": "sunil@example.com",
        "otp_type": "email",
    })
    assert forgot_resp.status_code == 200
    reset_otp = forgot_resp.json().get("dev_otp")

    # Reset password
    reset_resp = client.post("/api/auth/reset-password", json={
        "identifier": "sunil@example.com",
        "otp_code": reset_otp,
        "otp_type": "email",
        "new_password": "NewPassword123!",
        "confirm_password": "NewPassword123!",
    })
    assert reset_resp.status_code == 200

    # Verify old password fails, new password succeeds
    login_old = client.post("/api/auth/login", json={
        "identifier": "sunil@example.com",
        "password": "OldPassword123!",
    })
    assert login_old.status_code == 401

    login_new = client.post("/api/auth/login", json={
        "identifier": "sunil@example.com",
        "password": "NewPassword123!",
    })
    assert login_new.status_code == 200
