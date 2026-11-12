"""API endpoint tests using FastAPI TestClient with MOCK_GNANI=1."""

import os
import sys
from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Enforce MOCK_GNANI=1 before importing app
import app.config
import app.gnani
app.config.MOCK_GNANI = True
app.gnani.MOCK_GNANI = True

from app.db import Customer, Entry, create_db_and_tables, get_session
from app.main import app
from app.audio import convert_to_wav


from tests.conftest import shared_engine as test_engine

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health & Config
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_config():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert "shop_name" in resp.json()


# ---------------------------------------------------------------------------
# Transcribe Endpoint
# ---------------------------------------------------------------------------

def test_transcribe_success_mock():
    # Mock convert_to_wav to bypass local ffmpeg binary dependency
    with patch("app.main.convert_to_wav", return_value=b"RIFFmockwavdata"):
        files = {"file": ("test.webm", b"mockwebmbytes", "audio/webm")}
        resp = client.post("/api/transcribe", files=files)
        assert resp.status_code == 200
        data = resp.json()

        assert "transcript" in data
        assert data["transcript"] == "Sharma ji ko 5 kilo chawal, 600 rupaye, udhaar"
        assert "parsed" in data
        assert data["parsed"]["customer"] == "Sharma ji"
        assert data["parsed"]["item"] == "rice"
        assert data["parsed"]["amount"] == 600
        assert data["parsed"]["kind"] == "credit"
        # Since customer isn't in db yet, matched_customer is None
        assert data["matched_customer"] is None


def test_transcribe_with_existing_customer():
    # First create Sharma ji in the DB
    with Session(test_engine) as s:
        c = Customer(name="Sharma ji")
        s.add(c)
        s.commit()
        s.refresh(c)
        sharma_id = c.id

    with patch("app.main.convert_to_wav", return_value=b"RIFFmockwavdata"):
        files = {"file": ("test.webm", b"mockwebmbytes", "audio/webm")}
        resp = client.post("/api/transcribe", files=files)
        assert resp.status_code == 200
        data = resp.json()

        assert data["matched_customer"] is not None
        assert data["matched_customer"]["id"] == sharma_id
        assert data["matched_customer"]["name"] == "Sharma ji"


def test_transcribe_empty_file():
    files = {"file": ("empty.webm", b"", "audio/webm")}
    resp = client.post("/api/transcribe", files=files)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Entries: Creation, Validation & Balance
# ---------------------------------------------------------------------------

def test_create_entry_validation_errors():
    # 1. Missing customer
    resp = client.post("/api/entries", json={"customer": "", "amount": 100, "kind": "credit", "item": "rice"})
    assert resp.status_code == 422

    # 2. Amount <= 0
    resp = client.post("/api/entries", json={"customer": "Ramesh", "amount": 0, "kind": "credit", "item": "rice"})
    assert resp.status_code == 422

    # 3. Invalid kind
    resp = client.post("/api/entries", json={"customer": "Ramesh", "amount": 100, "kind": "unknown", "item": "rice"})
    assert resp.status_code == 422

    # 4. Missing item when kind is credit
    resp = client.post("/api/entries", json={"customer": "Ramesh", "amount": 100, "kind": "credit", "item": ""})
    assert resp.status_code == 422


def test_entries_flow_and_balances():
    # 1. Add credit entry: Ramesh, 600 udhaar (credit) -> balance 600
    resp = client.post(
        "/api/entries",
        json={
            "customer": "Ramesh Gupta",
            "amount": 600,
            "kind": "credit",
            "item": "rice",
            "quantity": 5,
            "unit": "kg",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance"] == 600
    entry_id = data["entry"]["id"]
    customer_id = data["entry"]["customer_id"]

    # 2. Add payment entry: Ramesh, 200 payment (no item required) -> balance 400
    resp = client.post(
        "/api/entries",
        json={
            "customer": "Ramesh Gupta",
            "amount": 200,
            "kind": "payment",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["balance"] == 400

    # 3. Add cash entry: Ramesh, 150 cash -> balance remains 400
    resp = client.post(
        "/api/entries",
        json={
            "customer": "Ramesh Gupta",
            "amount": 150,
            "kind": "cash",
            "item": "soap",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["balance"] == 400

    # 4. Check GET /api/customers
    resp = client.get("/api/customers")
    assert resp.status_code == 200
    customers = resp.json()
    ramesh = next(c for c in customers if c["id"] == customer_id)
    assert ramesh["balance"] == 400
    assert ramesh["last_activity"] is not None

    # 5. Check GET /api/customers/{id}/entries
    resp = client.get(f"/api/customers/{customer_id}/entries")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 3

    # 6. Check non-existent customer ledger -> 404
    resp = client.get("/api/customers/999999/entries")
    assert resp.status_code == 404

    # 7. Check GET /api/entries/{id}/invoice.pdf
    resp = client.get(f"/api/entries/{entry_id}/invoice.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0


# ---------------------------------------------------------------------------
# Invoice PDF Endpoint Dedicated Tests
# ---------------------------------------------------------------------------

def test_invoice_pdf_saved_entry_and_missing_404():
    # 1. Saved entry returns valid PDF
    create_resp = client.post(
        "/api/entries",
        json={
            "customer": "Invoice Test Customer",
            "amount": 350.0,
            "kind": "credit",
            "item": "mustard oil",
            "quantity": 2.0,
            "unit": "litre",
        },
    )
    assert create_resp.status_code == 200
    entry_id = create_resp.json()["entry"]["id"]

    pdf_resp = client.get(f"/api/entries/{entry_id}/invoice.pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
    assert len(pdf_resp.content) > 1000

    # 2. Missing entry returns 404
    missing_resp = client.get("/api/entries/999999/invoice.pdf")
    assert missing_resp.status_code == 404



# ---------------------------------------------------------------------------
# Speak (TTS)
# ---------------------------------------------------------------------------

def test_speak_endpoint():
    resp = client.post("/api/speak", json={"text": "Sharma ji ke khate mein 600 rupaye jod diye"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert len(resp.content) > 0

    # Empty text -> 400
    resp = client.post("/api/speak", json={"text": "   "})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Audio Conversion Error
# ---------------------------------------------------------------------------

def test_audio_convert_to_wav_missing_ffmpeg():
    # If ffmpeg is not installed or not in PATH, convert_to_wav must raise RuntimeError
    with patch("app.audio.get_ffmpeg_binary", return_value=None):
        import pytest
        with pytest.raises(RuntimeError, match="ffmpeg is not installed"):
            convert_to_wav(b"some audio bytes")
