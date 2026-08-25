"""Milestone 4 checklist step 14 - faculty dashboard: auth gating,
cross-student aggregation, summary generation/persistence, and health
indicator correctness. Patches app.routers.faculty.run_faculty_summary_agent
(same module-boundary reasoning as the other test files).
"""
from app.schemas import ProjectSummaryAgentOutput
from tests.conftest import auth_headers, make_faculty, register_and_login
from tests.test_pipeline import _patch_full_pipeline, submit_idea


def test_dashboard_requires_faculty(client, monkeypatch):
    _patch_full_pipeline(monkeypatch)
    token = register_and_login(client, email="notfaculty@test.com")
    resp = client.get("/api/faculty/dashboard", headers=auth_headers(token))
    assert resp.status_code == 403


def test_dashboard_lists_ideas_across_multiple_students(client, monkeypatch):
    _patch_full_pipeline(monkeypatch)
    token_a = register_and_login(client, email="studenta@test.com")
    token_b = register_and_login(client, email="studentb@test.com")
    submit_idea(client, token_a, title="Idea A")
    submit_idea(client, token_b, title="Idea B")

    ftoken = register_and_login(client, email="prof@test.com")
    make_faculty("prof@test.com")

    resp = client.get("/api/faculty/dashboard", headers=auth_headers(ftoken))
    assert resp.status_code == 200
    rows = resp.json()
    titles = {r["idea"]["title"] for r in rows}
    assert titles == {"Idea A", "Idea B"}
    emails = {r["student_email"] for r in rows}
    assert emails == {"studenta@test.com", "studentb@test.com"}


def test_summary_generation_persists_and_shows_on_dashboard(client, monkeypatch):
    _patch_full_pipeline(monkeypatch)
    stoken = register_and_login(client, email="s1@test.com")
    idea_id = submit_idea(client, stoken)

    ftoken = register_and_login(client, email="prof2@test.com")
    make_faculty("prof2@test.com")

    fake_summary = ProjectSummaryAgentOutput(
        summary="Off to a strong start, on pace with the plan.", health_status="on_track"
    )
    monkeypatch.setattr(
        "app.routers.faculty.run_faculty_summary_agent", lambda *a, **k: fake_summary
    )

    resp = client.post(f"/api/faculty/ideas/{idea_id}/summary", headers=auth_headers(ftoken))
    assert resp.status_code == 200
    assert resp.json()["health_status"] == "on_track"

    dash = client.get("/api/faculty/dashboard", headers=auth_headers(ftoken)).json()
    row = next(r for r in dash if r["idea"]["idea_id"] == idea_id)
    assert row["latest_summary"]["health_status"] == "on_track"

    # Audit trail: generating a second time adds a row, doesn't overwrite.
    fake_summary_2 = ProjectSummaryAgentOutput(summary="Update.", health_status="at_risk")
    monkeypatch.setattr(
        "app.routers.faculty.run_faculty_summary_agent", lambda *a, **k: fake_summary_2
    )
    client.post(f"/api/faculty/ideas/{idea_id}/summary", headers=auth_headers(ftoken))

    from app.database import SessionLocal
    from app.models import ProjectSummary

    db = SessionLocal()
    try:
        assert db.query(ProjectSummary).filter(ProjectSummary.idea_id == idea_id).count() == 2
    finally:
        db.close()


def test_summary_409_before_analyzed(client, monkeypatch):
    token = register_and_login(client, email="s2@test.com")
    resp = client.post(
        "/api/ideas", json={"title": "T", "description": "D"}, headers=auth_headers(token)
    )
    idea_id = resp.json()["idea_id"]

    ftoken = register_and_login(client, email="prof3@test.com")
    make_faculty("prof3@test.com")

    resp = client.post(f"/api/faculty/ideas/{idea_id}/summary", headers=auth_headers(ftoken))
    assert resp.status_code == 409


def test_detail_view_404_for_nonexistent_idea(client, monkeypatch):
    ftoken = register_and_login(client, email="prof4@test.com")
    make_faculty("prof4@test.com")
    resp = client.get("/api/faculty/ideas/does-not-exist", headers=auth_headers(ftoken))
    assert resp.status_code == 404


def test_health_indicators_computed_correctly(client, monkeypatch):
    """Exercises _compute_health_indicators indirectly through the dashboard
    endpoint, against known fixture data - the same values hand-verified
    against a real seeded DB during Milestone 4 step 6."""
    _patch_full_pipeline(monkeypatch)
    stoken = register_and_login(client, email="s3@test.com")
    idea_id = submit_idea(client, stoken)

    # Log progress for weeks 1 and 2 - weeks_completed should be 2 (the max
    # week_number), NOT derived from any "Completed:" text in the timeline.
    client.post(
        f"/api/ideas/{idea_id}/progress",
        json={"week_number": 1, "update_text": "Week 1 done."},
        headers=auth_headers(stoken),
    )
    client.post(
        f"/api/ideas/{idea_id}/progress",
        json={"week_number": 2, "update_text": "Week 2 in progress."},
        headers=auth_headers(stoken),
    )
    client.post(
        f"/api/ideas/{idea_id}/chat",
        json={"content": "hello"},
        headers=auth_headers(stoken),
    )
    # run_mentor_agent isn't patched here on purpose - the chat call itself
    # would 503 against the placeholder key, but the student message is
    # still persisted before that call happens (see ideas.py), so
    # chat_message_count should still register the one student turn.

    ftoken = register_and_login(client, email="prof5@test.com")
    make_faculty("prof5@test.com")

    dash = client.get("/api/faculty/dashboard", headers=auth_headers(ftoken)).json()
    row = next(r for r in dash if r["idea"]["idea_id"] == idea_id)
    assert row["weeks_completed"] == 2
    assert row["weeks_total"] == 2  # from _patch_full_pipeline's FAKE_TIMELINE (2 weeks)
    assert row["chat_message_count"] == 1
    assert row["replan_count"] == 0
    assert row["days_since_last_progress"] == 0
