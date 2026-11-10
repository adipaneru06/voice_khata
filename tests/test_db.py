"""Tests for app/db.py — uses in-memory SQLite, no files on disk."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, SQLModel, create_engine

from app.db import (
    Customer,
    Entry,
    add_entry,
    create_db_and_tables,
    find_or_create_customer,
    get_customers_with_balance,
    get_entries,
)


def _make_session():
    """Return a Session backed by a fresh in-memory database."""
    engine = create_engine("sqlite://", echo=False)
    create_db_and_tables(engine)
    return Session(engine)


# ── Balance: credit only ─────────────────────────────────────────────────

def test_balance_credit_only():
    s = _make_session()
    c = find_or_create_customer(s, "Sharma ji")
    add_entry(s, c.id, amount=600, kind="credit", item="rice")
    add_entry(s, c.id, amount=200, kind="credit", item="sugar")

    rows = get_customers_with_balance(s)
    assert len(rows) == 1
    assert rows[0]["balance"] == 800


# ── Balance: credit + payment ────────────────────────────────────────────

def test_balance_credit_plus_payment():
    s = _make_session()
    c = find_or_create_customer(s, "Ramesh")
    add_entry(s, c.id, amount=500, kind="credit", item="oil")
    add_entry(s, c.id, amount=300, kind="payment")

    rows = get_customers_with_balance(s)
    assert rows[0]["balance"] == 200  # 500 − 300


# ── Cash does NOT affect balance ─────────────────────────────────────────

def test_cash_does_not_change_balance():
    s = _make_session()
    c = find_or_create_customer(s, "Gupta ji")
    add_entry(s, c.id, amount=400, kind="credit", item="flour")
    add_entry(s, c.id, amount=150, kind="cash", item="soap")

    rows = get_customers_with_balance(s)
    assert rows[0]["balance"] == 400  # cash ignored


# ── Fuzzy matching: 'Sharma' and 'Sharma ji' → same customer ─────────────

def test_fuzzy_match_ignores_ji():
    s = _make_session()
    c1 = find_or_create_customer(s, "Sharma ji")
    c2 = find_or_create_customer(s, "Sharma")

    assert c1.id == c2.id  # same row


def test_fuzzy_match_case_insensitive():
    s = _make_session()
    c1 = find_or_create_customer(s, "ramesh")
    c2 = find_or_create_customer(s, "Ramesh")

    assert c1.id == c2.id


# ── last_activity ────────────────────────────────────────────────────────

def test_last_activity_is_latest_entry():
    s = _make_session()
    c = find_or_create_customer(s, "Verma")
    e1 = add_entry(s, c.id, amount=100, kind="credit", item="tea")
    e2 = add_entry(s, c.id, amount=50, kind="cash", item="salt")

    rows = get_customers_with_balance(s)
    # last_activity must equal the newest entry's timestamp
    assert rows[0]["last_activity"] == e2.created_at.isoformat()


def test_last_activity_null_when_no_entries():
    s = _make_session()
    c = find_or_create_customer(s, "Empty")

    rows = get_customers_with_balance(s)
    assert rows[0]["last_activity"] is None


# ── get_entries returns entries for customer ─────────────────────────────

def test_get_entries_returns_newest_first():
    s = _make_session()
    c = find_or_create_customer(s, "Ali")
    e1 = add_entry(s, c.id, amount=100, kind="credit", item="rice")
    e2 = add_entry(s, c.id, amount=200, kind="credit", item="sugar")

    entries = get_entries(s, c.id)
    assert len(entries) == 2
    # Newest first
    assert entries[0].id == e2.id
    assert entries[1].id == e1.id

