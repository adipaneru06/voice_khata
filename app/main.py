"""Voice Khata — FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.audio import convert_to_wav
from app.config import SHOP_NAME
from app.db import (
    Customer,
    Entry,
    add_entry,
    compute_balance,
    create_db_and_tables,
    delete_customer,
    delete_entry,
    find_customer,
    find_or_create_customer,
    get_customers_with_balance,
    get_entries,
    get_session,
)
from app.gnani import speech_to_text, text_to_speech
from app.invoice import generate_invoice
from app.parser import parse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on startup
    create_db_and_tables()
    yield


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Voice Khata", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request/Response Schemas
# ---------------------------------------------------------------------------

class EntryCreate(BaseModel):
    customer: str
    amount: float
    kind: str  # "credit" | "cash" | "payment"
    item: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    raw_transcript: Optional[str] = None


class SpeakRequest(BaseModel):
    text: str


class ParseRequest(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Health & Config
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def get_config():
    return {"shop_name": SHOP_NAME}


# ---------------------------------------------------------------------------
# Transcription Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Receive an audio upload, convert to WAV, transcribe with Gnani, and parse."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    try:
        wav_bytes = convert_to_wav(audio_bytes, filename=file.filename or "recording.webm")
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{str(exc)}",
        )

    try:
        transcript = await speech_to_text(wav_bytes)
    except Exception as exc:
        exc_str = str(exc)
        if "empty transcript" in exc_str.lower() or "no speech" in exc_str.lower():
            raise HTTPException(
                status_code=400,
                detail="No speech detected. Please speak clearly and try again.",
            )
        raise HTTPException(
            status_code=502,
            detail=f"Transcription failed: {exc_str}",
        )

    if not transcript or not transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="No speech detected. Please speak clearly and try again.",
        )

    parsed = parse(transcript)

    matched_customer = None
    if parsed.get("customer"):
        existing = find_customer(session, parsed["customer"])
        if existing:
            bal = compute_balance(session, existing.id)  # type: ignore[arg-type]
            matched_customer = {
                "id": existing.id,
                "name": existing.name,
                "balance": int(bal) if bal.is_integer() else bal,
            }

    return {
        "transcript": transcript,
        "parsed": parsed,
        "matched_customer": matched_customer,
    }


@app.post("/api/parse")
def parse_transcript_text(
    payload: ParseRequest,
    session: Session = Depends(get_session),
):
    """Directly parse a text transcript (e.g. for quick chips or manual entry) without audio."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    parsed = parse(text)
    matched_customer = None
    if parsed.get("customer"):
        existing = find_customer(session, parsed["customer"])
        if existing:
            bal = compute_balance(session, existing.id)  # type: ignore[arg-type]
            matched_customer = {
                "id": existing.id,
                "name": existing.name,
                "balance": int(bal) if bal.is_integer() else bal,
            }

    return {
        "transcript": text,
        "parsed": parsed,
        "matched_customer": matched_customer,
    }


# ---------------------------------------------------------------------------
# Entries & Customers Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/entries")
def create_entry(
    payload: EntryCreate,
    session: Session = Depends(get_session),
):
    """Validate entry, find/create customer, save entry, and return updated balance."""
    customer_name = payload.customer.strip()
    if not customer_name:
        raise HTTPException(status_code=422, detail="Customer name is required.")

    if payload.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be greater than 0.")

    if payload.kind not in ("credit", "cash", "payment"):
        raise HTTPException(
            status_code=422,
            detail="Kind must be one of: 'credit', 'cash', or 'payment'.",
        )

    # Item is required unless kind is payment
    if payload.kind != "payment":
        if not payload.item or not payload.item.strip():
            raise HTTPException(
                status_code=422,
                detail="Item is required unless type is payment.",
            )

    customer = find_or_create_customer(session, customer_name)

    entry = add_entry(
        session=session,
        customer_id=customer.id,  # type: ignore[arg-type]
        amount=payload.amount,
        kind=payload.kind,
        item=payload.item.strip() if payload.item else None,
        quantity=payload.quantity,
        unit=payload.unit,
        raw_transcript=payload.raw_transcript,
    )

    updated_balance = compute_balance(session, customer.id)  # type: ignore[arg-type]

    return {
        "entry": entry,
        "balance": updated_balance,
    }


@app.get("/api/customers")
def list_customers(session: Session = Depends(get_session)):
    """List customers with balance and last_activity."""
    return get_customers_with_balance(session)


@app.get("/api/customers/{id}/entries")
def customer_ledger(id: int, session: Session = Depends(get_session)):
    """Get ledger entries for a single customer."""
    customer = session.get(Customer, id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    return get_entries(session, id)


@app.get("/api/entries/recent")
def list_recent_entries(session: Session = Depends(get_session), limit: int = 20):
    """Get recent entries across all customers for dashboard scrolling feed."""
    from sqlmodel import select
    entries = session.exec(
        select(Entry).order_by(Entry.created_at.desc()).limit(limit)  # type: ignore[union-attr]
    ).all()
    result = []
    for e in entries:
        cust = session.get(Customer, e.customer_id)
        result.append({
            "id": e.id,
            "customer_id": e.customer_id,
            "customer_name": cust.name if cust else "Unknown",
            "item": e.item,
            "quantity": e.quantity,
            "unit": e.unit,
            "amount": e.amount,
            "kind": e.kind,
            "raw_transcript": e.raw_transcript,
            "created_at": e.created_at.isoformat(),
        })
    return result


@app.delete("/api/entries/{id}")
def delete_entry_endpoint(id: int, session: Session = Depends(get_session)):
    """Delete an entry and return updated customer balance."""
    entry = session.get(Entry, id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")

    cust_id = entry.customer_id
    delete_entry(session, id)
    new_balance = compute_balance(session, cust_id)
    return {
        "status": "ok",
        "deleted_id": id,
        "customer_id": cust_id,
        "balance": new_balance,
    }


@app.delete("/api/customers/{id}")
def delete_customer_endpoint(id: int, session: Session = Depends(get_session)):
    """Delete a customer and all their ledger entries."""
    success = delete_customer(session, id)
    if not success:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return {"status": "ok", "deleted_customer_id": id}


@app.get("/api/entries/{id}/invoice.pdf")
def get_invoice_pdf(id: int, session: Session = Depends(get_session)):
    """Generate and return one-page PDF invoice."""
    entry = session.get(Entry, id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")

    customer = session.get(Customer, entry.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found for this entry.")

    balance = compute_balance(session, customer.id)  # type: ignore[arg-type]

    pdf_path = generate_invoice(
        entry_id=entry.id,  # type: ignore[arg-type]
        shop_name=SHOP_NAME,
        customer_name=customer.name,
        item=entry.item,
        quantity=entry.quantity,
        unit=entry.unit,
        amount=entry.amount,
        kind=entry.kind,
        balance=balance,
        created_at=entry.created_at,
    )

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"invoice_{entry.id}.pdf",
    )


# ---------------------------------------------------------------------------
# TTS Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/speak")
async def speak(payload: SpeakRequest):
    """Synthesize text to speech using Gnani Timbre."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        audio_bytes = await text_to_speech(text)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Speech synthesis failed: {str(exc)}",
        )

    return Response(content=audio_bytes, media_type="audio/wav")


# ---------------------------------------------------------------------------
# Static frontend files (Do not modify contents)
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

@app.get("/")
def index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Voice Khata API is running."}

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
