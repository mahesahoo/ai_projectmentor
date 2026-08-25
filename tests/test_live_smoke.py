"""Milestone 4 checklist step 15 - the test(s) in this suite that hit the
real Gemini API. Deselected by default (see pytest.ini: `-m "not live"`);
run explicitly with `pytest -m live` after exporting a real GEMINI_API_KEY.

Everything else in tests/ mocks the run_*_agent calls to stay fast and
deterministic - this file is the check that the actual wiring (prompts,
schemas, the google-genai client) still works end to end for EVERY agent,
per the Milestone 4 brief's literal wording ("end-to-end testing across all
agents and interaction workflows") - not just the 5-agent pipeline.

Known constraint: this makes ~9 real Gemini calls in quick succession, which
can exceed the free tier's per-minute burst limit (5 requests/minute) if run
back-to-back with other live testing on the same key - a different failure
mode than the daily quota limit, and one that clears within about a minute.
If a run fails partway through with a `503`, that's very likely this, not a
regression - check how recently the key made other live calls before
assuming otherwise.
"""
import os

import pytest

from tests.conftest import auth_headers, make_faculty, register_and_login

_PLACEHOLDER_KEY = "test-placeholder-key-not-a-real-key"

live_only = pytest.mark.skipif(
    os.environ.get("GEMINI_API_KEY", _PLACEHOLDER_KEY) == _PLACEHOLDER_KEY,
    reason="No real GEMINI_API_KEY set - export one before running `pytest -m live`.",
)


@pytest.mark.live
@live_only
def test_real_full_lifecycle_all_nine_agents(client):
    """One continuous live run touching all 9 agents: the 5-agent pipeline,
    chat, replan (timeline + risk again), a document, and the faculty
    summary - the automated equivalent of every manual live rehearsal this
    project has done by hand across M2-M4."""
    stoken = register_and_login(client, email="livesmoke@test.com")
    resp = client.post(
        "/api/ideas",
        json={
            "title": "Campus Lost & Found Tracker",
            "description": (
                "A web app where students can post items they lost or found on campus, "
                "search by category/location, and get notified on matches."
            ),
        },
        headers=auth_headers(stoken),
    )
    assert resp.status_code == 201
    idea_id = resp.json()["idea_id"]

    # 1-5: TestClient blocks until the BackgroundTask (the real pipeline)
    # finishes - no polling needed, unlike a manual browser rehearsal.
    status_resp = client.get(f"/api/ideas/{idea_id}", headers=auth_headers(stoken))
    assert status_resp.json()["status"] == "analyzed", (
        "Pipeline failed against the real API - check GEMINI_API_KEY validity "
        "and quota before assuming a code regression."
    )
    bp = client.get(f"/api/ideas/{idea_id}/blueprint", headers=auth_headers(stoken)).json()
    assert bp["feasibility"] and bp["scope"] and bp["tech"] and bp["timeline"] and bp["risk"]

    # 6: Conversational Mentor
    chat_resp = client.post(
        f"/api/ideas/{idea_id}/chat",
        json={"content": "What's the riskiest part of this project?"},
        headers=auth_headers(stoken),
    )
    assert chat_resp.status_code == 200
    assert len(chat_resp.json()["content"]) > 0

    # Free DB write, no agent call - sets up real progress for replan/docs below
    client.post(
        f"/api/ideas/{idea_id}/progress",
        json={"week_number": 1, "update_text": "Backend scaffold done, auth took 3 extra days."},
        headers=auth_headers(stoken),
    )

    # 7 (+ 5 again): Replan re-runs Timeline and Risk
    replan_resp = client.post(f"/api/ideas/{idea_id}/replan", headers=auth_headers(stoken))
    assert replan_resp.status_code == 200
    assert len(replan_resp.json()["timeline"]["weeks"]) > 0

    # 8: Documentation Generation
    doc_resp = client.post(
        f"/api/ideas/{idea_id}/documents",
        json={"doc_type": "progress_report"},
        headers=auth_headers(stoken),
    )
    assert doc_resp.status_code == 200
    assert len(doc_resp.json()["content"]) > 0

    # 9: Faculty Summary
    ftoken = register_and_login(client, email="livesmoke-faculty@test.com")
    make_faculty("livesmoke-faculty@test.com")
    summary_resp = client.post(
        f"/api/faculty/ideas/{idea_id}/summary", headers=auth_headers(ftoken)
    )
    assert summary_resp.status_code == 200
    assert summary_resp.json()["health_status"] in (
        "on_track", "at_risk", "stalled", "not_feasible",
    )
