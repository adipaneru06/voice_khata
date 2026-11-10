"""SQLite data models and query helpers (SQLModel + SQLite).

Uses difflib for fuzzy customer matching. No extra dependencies.
"""

import difflib
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Entry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    item: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    amount: float
    kind: str  # "credit" | "cash" | "payment"
    raw_transcript: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Engine / helpers
# ---------------------------------------------------------------------------

DATABASE_URL = "sqlite:///voice_khata.db"
engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables(eng=None):
    """Create all tables. Pass *eng* to use a custom engine (e.g. in-memory for tests)."""
    SQLModel.metadata.create_all(eng or engine)


def get_session():
    """FastAPI dependency for database session."""
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Fuzzy customer matching
# ---------------------------------------------------------------------------

_HONORIFICS = {"ji", "जी"}


def _normalize_name(name: str) -> str:
    """Lower-case and strip honorifics for comparison."""
    tokens = [t for t in name.lower().split() if t not in _HONORIFICS]
    return " ".join(tokens)


def find_customer(session: Session, name: str) -> Optional[Customer]:
    """Find an existing customer by fuzzy name match, or None if not found."""
    norm_input = _normalize_name(name)
    customers = session.exec(select(Customer)).all()

    best_match: Optional[Customer] = None
    best_ratio: float = 0.0

    for c in customers:
        norm_existing = _normalize_name(c.name)
        if norm_existing == norm_input:
            return c
        ratio = difflib.SequenceMatcher(None, norm_input, norm_existing).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = c

    if best_match is not None and best_ratio >= 0.8:
        return best_match

    return None


def find_or_create_customer(session: Session, name: str) -> Customer:
    """Find an existing customer by fuzzy name match, or create a new one."""
    existing = find_customer(session, name)
    if existing is not None:
        return existing

    # No match — create new customer, preserving the spoken name
    customer = Customer(name=name)
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


# ---------------------------------------------------------------------------
# Entry helpers
# ---------------------------------------------------------------------------

def add_entry(
    session: Session,
    customer_id: int,
    amount: float,
    kind: str,
    item: Optional[str] = None,
    quantity: Optional[float] = None,
    unit: Optional[str] = None,
    raw_transcript: Optional[str] = None,
) -> Entry:
    """Insert an entry and return it."""
    entry = Entry(
        customer_id=customer_id,
        item=item,
        quantity=quantity,
        unit=unit,
        amount=amount,
        kind=kind,
        raw_transcript=raw_transcript,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def get_entries(session: Session, customer_id: int) -> list[Entry]:
    """Return all entries for a customer, newest first."""
    return list(
        session.exec(
            select(Entry)
            .where(Entry.customer_id == customer_id)
            .order_by(Entry.created_at.desc())  # type: ignore[union-attr]
        ).all()
    )


def delete_entry(session: Session, entry_id: int) -> Optional[Entry]:
    """Delete an entry by ID and return the deleted entry (or None if not found)."""
    entry = session.get(Entry, entry_id)
    if not entry:
        return None
    session.delete(entry)
    session.commit()
    return entry


def delete_customer(session: Session, customer_id: int) -> bool:
    """Delete a customer and all their associated entries."""
    customer = session.get(Customer, customer_id)
    if not customer:
        return False
    entries = session.exec(select(Entry).where(Entry.customer_id == customer_id)).all()
    for e in entries:
        session.delete(e)
    session.delete(customer)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Balance & customer list
# ---------------------------------------------------------------------------

def compute_balance(session: Session, customer_id: int) -> float:
    """balance = sum(credit) − sum(payment). Cash is ignored."""
    entries = session.exec(
        select(Entry).where(Entry.customer_id == customer_id)
    ).all()
    balance = 0.0
    for e in entries:
        if e.kind == "credit":
            balance += e.amount
        elif e.kind == "payment":
            balance -= e.amount
    return balance


def get_customers_with_balance(session: Session) -> list[dict]:
    """Return id, name, balance, last_activity for every customer."""
    customers = session.exec(select(Customer)).all()
    result = []
    for c in customers:
        balance = compute_balance(session, c.id)
        last_entry = session.exec(
            select(Entry)
            .where(Entry.customer_id == c.id)
            .order_by(Entry.created_at.desc())  # type: ignore[union-attr]
        ).first()
        result.append({
            "id": c.id,
            "name": c.name,
            "balance": balance,
            "last_activity": last_entry.created_at.isoformat() if last_entry else None,
        })
    return result
