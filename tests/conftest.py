"""Milestone 4 test suite setup.

CRITICAL ORDERING: DATABASE_URL (and a placeholder GEMINI_API_KEY) must be
set BEFORE any `app.*` module is imported anywhere - app/database.py reads
DATABASE_URL at import time into module-level engine/SessionLocal singletons,
and app/agents/pipeline.py's background task (trigger_agent_pipeline in
app/routers/ideas.py) calls SessionLocal() directly rather than going through
FastAPI's `Depends(get_db)` - so a plain `app.dependency_overrides[get_db]`
override would NOT catch the background pipeline; it would still hit whatever
DATABASE_URL was set at import time. Setting the env var here, before the
`import app.main` below, is what actually isolates every code path (both the
DI-based request handlers and the background task) from the real
project_mentor.db.

File-based SQLite, not `:memory:`: an in-memory DB is connection-scoped, and
SQLAlchemy's default engine opens a new connection per checkout - without
`poolclass=StaticPool` (which app/database.py's create_engine() call doesn't
set, since it's written for a real DATABASE_URL, not test isolation), each
new connection would see an empty, different in-memory DB. A throwaway file
sidesteps that entirely with zero extra wiring.
"""
import os
import tempfile

_TEST_DB_DIR = tempfile.mkdtemp(prefix="project_mentor_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/test.db"
os.environ.setdefault("GEMINI_API_KEY", "test-placeholder-key-not-a-real-key")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    """Fresh TestClient per test, with all tables dropped and recreated
    first - full isolation between tests without needing unique emails
    or other cross-test bookkeeping."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def register_and_login(client, email="student@test.com", password="TestPass123", name="Test Student"):
    """Shared helper: register + log in, return the bearer token."""
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def make_faculty(email):
    """Flips is_faculty=True directly via the ORM - there's no
    faculty-provisioning endpoint by design (see MILESTONE4_CHECKLIST.md's
    open question: a manual flip is enough for a milestone demo)."""
    from app.database import SessionLocal
    from app.models import Student

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.email == email).first()
        student.is_faculty = True
        db.commit()
    finally:
        db.close()
