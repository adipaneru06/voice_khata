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

class ShopOwner(SQLModel, table=True):
    __tablename__ = "shop_owner"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(index=True, unique=True)
    mobile_number: str = Field(index=True, unique=True)
    password_hash: str
    email_verified: bool = Field(default=False)
    phone_verified: bool = Field(default=False)
    account_status: str = Field(default="active")  # active | suspended | deactivated
    role: str = Field(default="owner")  # owner | admin
    profile_image: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None


class Shop(SQLModel, table=True):
    __tablename__ = "shop"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="shop_owner.id", index=True)
    shop_name: str = Field(default="My Shop")
    shop_category: str = Field(default="Grocery Store")
    custom_category: Optional[str] = None
    shop_description: Optional[str] = None
    shop_mobile_number: str = Field(default="")
    alternative_mobile_number: Optional[str] = None
    shop_email: Optional[str] = None
    opening_time: str = Field(default="09:00 AM")
    closing_time: str = Field(default="09:00 PM")
    weekly_closing_day: str = Field(default="None")
    house_number: Optional[str] = None
    building_name: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    city: str = Field(default="")
    state: str = Field(default="")
    pincode: str = Field(default="")
    country: str = Field(default="India")
    complete_address: str = Field(default="")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    profile_image: Optional[str] = None
    verification_status: str = Field(default="pending")  # pending | verified | rejected
    is_registration_complete: bool = Field(default=False)
    registration_step: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OTPVerification(SQLModel, table=True):
    __tablename__ = "otp_verification"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="shop_owner.id", index=True)
    target: str = Field(index=True)  # email or phone number
    otp_type: str = Field(default="email")  # email | phone
    otp_hash: str
    expires_at: datetime
    attempts: int = Field(default=0)
    is_used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ShopSession(SQLModel, table=True):
    __tablename__ = "shop_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="shop_owner.id", index=True)
    token: str = Field(unique=True, index=True)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    is_active: bool = Field(default=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LoginActivity(SQLModel, table=True):
    __tablename__ = "login_activity"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, index=True)
    identifier: str
    action: str  # login_success | login_failed | registered | otp_verified | password_reset | profile_updated
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    phone: Optional[str] = None
    shop_id: Optional[int] = Field(default=None, foreign_key="shop.id", index=True)
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
    """Create all tables and perform safe schema migrations."""
    e = eng or engine
    SQLModel.metadata.create_all(e)

    # Check and migrate customer table if shop_id is missing
    with e.connect() as conn:
        try:
            from sqlalchemy import text
            res = conn.execute(text("PRAGMA table_info(customer);")).fetchall()
            col_names = [r[1] for r in res]
            if "shop_id" not in col_names and len(col_names) > 0:
                conn.execute(text("ALTER TABLE customer ADD COLUMN shop_id INTEGER REFERENCES shop(id);"))
                conn.commit()
        except Exception:
            pass


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


def find_customer(session: Session, name: str, shop_id: Optional[int] = None) -> Optional[Customer]:
    """Find an existing customer by fuzzy name match, or None if not found."""
    norm_input = _normalize_name(name)
    query = select(Customer)
    if shop_id is not None:
        query = query.where(Customer.shop_id == shop_id)
    customers = session.exec(query).all()

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


def find_or_create_customer(session: Session, name: str, shop_id: Optional[int] = None) -> Customer:
    """Find an existing customer by fuzzy name match, or create a new one."""
    existing = find_customer(session, name, shop_id=shop_id)
    if existing is not None:
        return existing

    # No match — create new customer, preserving the spoken name
    customer = Customer(name=name, shop_id=shop_id)
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


def get_customers_with_balance(session: Session, shop_id: Optional[int] = None) -> list[dict]:
    """Return id, name, balance, last_activity for every customer."""
    query = select(Customer)
    if shop_id is not None:
        query = query.where(Customer.shop_id == shop_id)
    customers = session.exec(query).all()
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
