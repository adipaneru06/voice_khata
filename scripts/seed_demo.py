"""Seed demo data for filming Voice Khata.

Populates the database with realistic demo entries so the home screen and ledgers
match the design exactly:
  - Sharma ji:    ₹600
  - Ramesh:       ₹0
  - Gupta ji:     ₹280
  - Verma ji:     ₹1,450
  - Anita Stores: ₹320
  - Pintu:        ₹90
  Total Udhaar:   ₹2,740 (6 active customers)

Usage:
  python scripts/seed_demo.py --reset
  python scripts/seed_demo.py
"""

import argparse
from datetime import datetime, timedelta, timezone
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import Session, SQLModel, select
from app.db import Customer, Entry, compute_balance, create_db_and_tables, engine


def seed_database(reset: bool = False):
    """Seed demo data into the SQLite database."""
    if reset:
        print("Resetting database (dropping all tables)...")
        SQLModel.metadata.drop_all(engine)

    # Ensure tables exist
    create_db_and_tables(engine)

    with Session(engine) as session:
        existing_count = len(session.exec(select(Customer)).all())
        if existing_count > 0 and not reset:
            print(f"Notice: Database already has {existing_count} customers. Use --reset to wipe and re-seed.")
            return

        now = datetime.now(timezone.utc)

        # -------------------------------------------------------------------
        # Demo Data Definition
        # -------------------------------------------------------------------
        demo_customers = [
            {
                "name": "Sharma ji",
                "phone": "+91 98765 43210",
                "created_at": now - timedelta(days=21),
                "entries": [
                    {
                        "item": "Wheat Flour (Atta)",
                        "quantity": 10.0,
                        "unit": "kg",
                        "amount": 420.0,
                        "kind": "credit",
                        "raw_transcript": "Sharma ji ko 10 kilo atta 420 rupaye udhaar",
                        "created_at": now - timedelta(days=18, hours=2),
                    },
                    {
                        "item": "Mustard Oil",
                        "quantity": 2.0,
                        "unit": "litre",
                        "amount": 380.0,
                        "kind": "credit",
                        "raw_transcript": "Sharma ji ko 2 litre tel 380 rupaye udhaar",
                        "created_at": now - timedelta(days=11, hours=5),
                    },
                    {
                        "item": None,
                        "quantity": None,
                        "unit": None,
                        "amount": 800.0,
                        "kind": "payment",
                        "raw_transcript": "Sharma ji ne 800 rupaye diye",
                        "created_at": now - timedelta(days=5, hours=3),
                    },
                    {
                        "item": "Rice",
                        "quantity": 5.0,
                        "unit": "kg",
                        "amount": 600.0,
                        "kind": "credit",
                        "raw_transcript": "Sharma ji ko 5 kilo chawal 600 rupaye udhaar",
                        "created_at": now - timedelta(hours=2, minutes=15),
                    },
                ],
            },
            {
                "name": "Ramesh",
                "phone": "+91 98111 22334",
                "created_at": now - timedelta(days=20),
                "entries": [
                    {
                        "item": "Sugar",
                        "quantity": 2.0,
                        "unit": "kg",
                        "amount": 100.0,
                        "kind": "credit",
                        "raw_transcript": "Ramesh ko do kilo cheeni 100 rupaye udhaar",
                        "created_at": now - timedelta(days=15, hours=4),
                    },
                    {
                        "item": "Toor Dal",
                        "quantity": 1.0,
                        "unit": "kg",
                        "amount": 150.0,
                        "kind": "credit",
                        "raw_transcript": "Ramesh ko ek kilo dal 150 rupaye udhaar",
                        "created_at": now - timedelta(days=9, hours=1),
                    },
                    {
                        "item": None,
                        "quantity": None,
                        "unit": None,
                        "amount": 250.0,
                        "kind": "payment",
                        "raw_transcript": "Ramesh ne 250 rupaye jama kiye",
                        "created_at": now - timedelta(days=4, hours=6),
                    },
                    {
                        "item": "Refined Oil",
                        "quantity": 1.0,
                        "unit": "litre",
                        "amount": 140.0,
                        "kind": "cash",
                        "raw_transcript": "Ramesh ko ek litre tel 140 cash",
                        "created_at": now - timedelta(days=1, hours=4),
                    },
                ],
            },
            {
                "name": "Gupta ji",
                "phone": "+91 97234 56789",
                "created_at": now - timedelta(days=19),
                "entries": [
                    {
                        "item": "Chana Dal",
                        "quantity": 2.0,
                        "unit": "kg",
                        "amount": 240.0,
                        "kind": "credit",
                        "raw_transcript": "Gupta ji ko 2 kilo dal 240 udhaar",
                        "created_at": now - timedelta(days=16, hours=3),
                    },
                    {
                        "item": None,
                        "quantity": None,
                        "unit": None,
                        "amount": 240.0,
                        "kind": "payment",
                        "raw_transcript": "Gupta ji ne 240 rupaye diye",
                        "created_at": now - timedelta(days=10, hours=2),
                    },
                    {
                        "item": "Mustard Oil",
                        "quantity": 2.0,
                        "unit": "litre",
                        "amount": 280.0,
                        "kind": "credit",
                        "raw_transcript": "Gupta ji ko do litre tel 280 udhaar",
                        "created_at": now - timedelta(days=2, hours=5),
                    },
                ],
            },
            {
                "name": "Verma ji",
                "phone": "+91 99887 76655",
                "created_at": now - timedelta(days=21),
                "entries": [
                    {
                        "item": "Basmati Rice",
                        "quantity": 10.0,
                        "unit": "kg",
                        "amount": 950.0,
                        "kind": "credit",
                        "raw_transcript": "Verma ji ko 10 kilo chawal 950 udhaar",
                        "created_at": now - timedelta(days=20, hours=4),
                    },
                    {
                        "item": None,
                        "quantity": None,
                        "unit": None,
                        "amount": 500.0,
                        "kind": "payment",
                        "raw_transcript": "Verma ji ne 500 rupaye diye",
                        "created_at": now - timedelta(days=13, hours=3),
                    },
                    {
                        "item": "Atta",
                        "quantity": 10.0,
                        "unit": "kg",
                        "amount": 450.0,
                        "kind": "credit",
                        "raw_transcript": "Verma ji ko 10 kilo atta 450 udhaar",
                        "created_at": now - timedelta(days=7, hours=2),
                    },
                    {
                        "item": "Sugar",
                        "quantity": 10.0,
                        "unit": "kg",
                        "amount": 550.0,
                        "kind": "credit",
                        "raw_transcript": "Verma ji ko 10 kilo cheeni 550 udhaar",
                        "created_at": now - timedelta(days=3, hours=6),
                    },
                ],
            },
            {
                "name": "Anita Stores",
                "phone": "+91 94567 12345",
                "created_at": now - timedelta(days=18),
                "entries": [
                    {
                        "item": "Sugar",
                        "quantity": 5.0,
                        "unit": "kg",
                        "amount": 220.0,
                        "kind": "credit",
                        "raw_transcript": "Anita Stores ko 5 kilo cheeni 220 udhaar",
                        "created_at": now - timedelta(days=14, hours=5),
                    },
                    {
                        "item": None,
                        "quantity": None,
                        "unit": None,
                        "amount": 220.0,
                        "kind": "payment",
                        "raw_transcript": "Anita Stores ne 220 diye",
                        "created_at": now - timedelta(days=8, hours=4),
                    },
                    {
                        "item": "Moong Dal",
                        "quantity": 2.0,
                        "unit": "kg",
                        "amount": 320.0,
                        "kind": "credit",
                        "raw_transcript": "Anita Stores ko 2 kilo dal 320 udhaar",
                        "created_at": now - timedelta(days=4, hours=2),
                    },
                ],
            },
            {
                "name": "Pintu",
                "phone": "+91 93456 78901",
                "created_at": now - timedelta(days=19),
                "entries": [
                    {
                        "item": "Atta",
                        "quantity": 1.0,
                        "unit": "kg",
                        "amount": 45.0,
                        "kind": "credit",
                        "raw_transcript": "Pintu ko ek kilo atta 45 udhaar",
                        "created_at": now - timedelta(days=17, hours=2),
                    },
                    {
                        "item": None,
                        "quantity": None,
                        "unit": None,
                        "amount": 45.0,
                        "kind": "payment",
                        "raw_transcript": "Pintu ne 45 rupaye diye",
                        "created_at": now - timedelta(days=12, hours=1),
                    },
                    {
                        "item": "Sugar",
                        "quantity": 2.0,
                        "unit": "kg",
                        "amount": 90.0,
                        "kind": "credit",
                        "raw_transcript": "Pintu ko 2 kilo cheeni 90 udhaar",
                        "created_at": now - timedelta(days=6, hours=3),
                    },
                ],
            },
        ]

        print("Seeding demo customers and entries...")
        total_udhaar = 0.0

        for cust_data in demo_customers:
            customer = Customer(
                name=cust_data["name"],
                phone=cust_data.get("phone"),
                created_at=cust_data["created_at"],
            )
            session.add(customer)
            session.commit()
            session.refresh(customer)

            for entry_data in cust_data["entries"]:
                entry = Entry(
                    customer_id=customer.id,
                    item=entry_data["item"],
                    quantity=entry_data["quantity"],
                    unit=entry_data["unit"],
                    amount=entry_data["amount"],
                    kind=entry_data["kind"],
                    raw_transcript=entry_data.get("raw_transcript"),
                    created_at=entry_data["created_at"],
                )
                session.add(entry)
            session.commit()

            balance = compute_balance(session, customer.id)
            if balance > 0:
                total_udhaar += balance

            print(f"  • {customer.name:14} (ID: {customer.id}): Balance = ₹{int(balance) if balance.is_integer() else balance}")

        print("-" * 50)
        print(f"Total Udhaar: ₹{int(total_udhaar) if total_udhaar.is_integer() else total_udhaar}")
        print(f"Active Customers: {len(demo_customers)}")
        print("Seeding completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data for filming Voice Khata.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the database before seeding demo data.",
    )
    args = parser.parse_args()
    seed_database(reset=args.reset)

