"""Milestone 4 checklist step 15 - the one test in this suite that hits the
real Gemini API. Deselected by default (see pytest.ini: `-m "not live"`);
run explicitly with `pytest -m live` after exporting a real GEMINI_API_KEY.

Everything else in tests/ mocks the run_*_agent calls to stay fast and
deterministic - this is the single check that the actual wiring (prompts,
schemas, the google-genai client) still works end to end, not just the
routing/persistence logic around it.
"""
import os

import pytest

from tests.conftest import auth_headers, register_and_login

_PLACEHOLDER_KEY = "test-placeholder-key-not-a-real-key"


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("GEMINI_API_KEY", _PLACEHOLDER_KEY) == _PLACEHOLDER_KEY,
    reason="No real GEMINI_API_KEY set - export one before running `pytest -m live`.",
)
def test_real_pipeline_produces_analyzed_blueprint(client):
    token = register_and_login(client, email="livesmoke@test.com")
    resp = client.post(
        "/api/ideas",
        json={
            "title": "Campus Lost & Found Tracker",
            "description": (
                "A web app where students can post items they lost or found on campus, "
                "search by category/location, and get notified on matches."
            ),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    idea_id = resp.json()["idea_id"]

    # TestClient blocks until the BackgroundTask (the real pipeline, this
    # time) finishes - this call takes real wall-clock time, ~40-45s
    # measured during the Milestone 3 rehearsal for all 5 agents.
    status_resp = client.get(f"/api/ideas/{idea_id}", headers=auth_headers(token))
    assert status_resp.json()["status"] in ("analyzed", "failed")
    assert status_resp.json()["status"] == "analyzed", (
        "Pipeline failed against the real API - check GEMINI_API_KEY validity "
        "and quota before assuming a code regression."
    )

    bp = client.get(f"/api/ideas/{idea_id}/blueprint", headers=auth_headers(token)).json()
    assert bp["feasibility"]["verdict"] in ("feasible", "risky", "not_feasible")
    assert bp["scope"] is not None
    assert bp["tech"] is not None
    assert len(bp["timeline"]["weeks"]) > 0
    assert len(bp["risk"]["risks"]) > 0
