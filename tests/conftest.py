"""Pytest shared test setup and fixtures."""

import os
import sys
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Enforce MOCK_GNANI=1
import app.config
import app.gnani
app.config.MOCK_GNANI = True
app.gnani.MOCK_GNANI = True

from app.db import create_db_and_tables, get_session
from app.main import app

shared_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
create_db_and_tables(shared_engine)


def override_session():
    with Session(shared_engine) as session:
        yield session


app.dependency_overrides[get_session] = override_session

