"""Milestone 4 checklist step 14 - chat/progress/replan/documents
routing, persistence, and 409-gating tests. Mocks patch
app.routers.ideas.run_mentor_agent / run_replan_agent / run_risk_agent /
run_docs_agent - that module imports each function directly into its own
namespace, so the patch target is ideas.py, not the underlying agent
module (same reasoning as test_pipeline.py).
"""
from app.schemas import FeasibilityAgentOutput, RiskAgentOutput, RiskItem, TimelineAgentOutput, WeekPlan
from tests.conftest import auth_headers, register_and_login
from tests.test_pipeline import _patch_full_pipeline, submit_idea


def analyzed_idea(client, monkeypatch, email="m3@test.com"):
    """Shared setup: a fully analyzed idea, ready for chat/progress/replan/docs."""
    _patch_full_pipeline(monkeypatch)
    token = register_and_login(client, email=email)
    idea_id = submit_idea(client, token)
    return token, idea_id


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


def test_chat_requires_analyzed_status(client, monkeypatch):
    token = register_and_login(client, email="notyet@test.com")
    # Submit without patching the pipeline agents at all - status will never
    # reach analyzed within this test, which is exactly what's being checked.
    resp = client.post(
        "/api/ideas",
        json={"title": "T", "description": "D"},
        headers=auth_headers(token),
    )
    idea_id = resp.json()["idea_id"]
    # The (unmocked) pipeline hits a placeholder key and fails fast, landing
    # on status="failed" - also not "analyzed", so the 409 gate still applies.
    resp = client.post(
        f"/api/ideas/{idea_id}/chat",
        json={"content": "hi"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409


def test_chat_persists_both_turns_and_threads_history(client, monkeypatch):
    calls = []

    def fake_mentor(*args, **kwargs):
        history = args[9] if len(args) > 9 else kwargs.get("history")
        new_message = args[10] if len(args) > 10 else kwargs.get("new_message")
        calls.append((list(history), new_message))
        return f"reply #{len(calls)}"

    monkeypatch.setattr("app.routers.ideas.run_mentor_agent", fake_mentor)
    token, idea_id = analyzed_idea(client, monkeypatch)

    r1 = client.post(
        f"/api/ideas/{idea_id}/chat", json={"content": "first question"}, headers=auth_headers(token)
    )
    assert r1.status_code == 200
    assert r1.json()["content"] == "reply #1"

    r2 = client.post(
        f"/api/ideas/{idea_id}/chat", json={"content": "second question"}, headers=auth_headers(token)
    )
    assert r2.json()["content"] == "reply #2"

    # Second call's history must include both turns from the first exchange.
    second_call_history = calls[1][0]
    assert ("student", "first question") in second_call_history
    assert ("mentor", "reply #1") in second_call_history

    history_resp = client.get(f"/api/ideas/{idea_id}/chat", headers=auth_headers(token))
    assert len(history_resp.json()) == 4  # 2 student + 2 mentor rows


def test_chat_agent_failure_returns_clean_503_not_bare_500(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("simulated upstream failure")

    monkeypatch.setattr("app.routers.ideas.run_mentor_agent", boom)
    token, idea_id = analyzed_idea(client, monkeypatch, email="chatfail@test.com")

    resp = client.post(
        f"/api/ideas/{idea_id}/chat", json={"content": "hi"}, headers=auth_headers(token)
    )
    assert resp.status_code == 503
    assert "detail" in resp.json()  # a real JSON body, not a bare error page


# ---------------------------------------------------------------------------
# Progress + replan
# ---------------------------------------------------------------------------


def test_progress_logging_is_free_no_agent_call(client, monkeypatch):
    # Deliberately no run_replan_agent/run_risk_agent patch - if logging
    # progress triggered any agent call, it would hit the placeholder key
    # and this test would fail loudly.
    token, idea_id = analyzed_idea(client, monkeypatch, email="progress@test.com")
    resp = client.post(
        f"/api/ideas/{idea_id}/progress",
        json={"week_number": 1, "update_text": "Backend scaffold done."},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    history = client.get(f"/api/ideas/{idea_id}/progress", headers=auth_headers(token)).json()
    assert len(history) == 1
    assert history[0]["update_text"] == "Backend scaffold done."


def test_replan_persists_new_rows_without_deleting_old(client, monkeypatch):
    token, idea_id = analyzed_idea(client, monkeypatch, email="replan@test.com")
    client.post(
        f"/api/ideas/{idea_id}/progress",
        json={"week_number": 1, "update_text": "Behind schedule."},
        headers=auth_headers(token),
    )

    new_timeline = TimelineAgentOutput(weeks=[WeekPlan(week=1, tasks=["Completed: scaffold"])])
    new_risk = RiskAgentOutput(
        risks=[RiskItem(risk="New blocker found", likelihood="high", mitigation="Fix it")]
    )
    monkeypatch.setattr("app.routers.ideas.run_replan_agent", lambda *a, **k: new_timeline)
    monkeypatch.setattr("app.routers.ideas.run_risk_agent", lambda *a, **k: new_risk)

    resp = client.post(f"/api/ideas/{idea_id}/replan", headers=auth_headers(token))
    assert resp.status_code == 200
    bp = resp.json()
    assert bp["timeline"]["weeks"][0]["tasks"] == ["Completed: scaffold"]
    assert bp["risk"]["risks"][0]["risk"] == "New blocker found"

    # Audit trail: 2 timeline rows and 2 risk rows now exist for this idea.
    from app.database import SessionLocal
    from app.models import RiskAssessment, TimelinePlan

    db = SessionLocal()
    try:
        assert db.query(TimelinePlan).filter(TimelinePlan.idea_id == idea_id).count() == 2
        assert db.query(RiskAssessment).filter(RiskAssessment.idea_id == idea_id).count() == 2
    finally:
        db.close()


def test_replan_409_when_nothing_to_replan(client, monkeypatch):
    fake_not_feasible = FeasibilityAgentOutput(verdict="not_feasible", reasoning="Undefined scope.")
    monkeypatch.setattr(
        "app.agents.pipeline.run_feasibility_agent", lambda *a, **k: fake_not_feasible
    )
    token = register_and_login(client, email="norepla@test.com")
    idea_id = submit_idea(client, token, title="App", description="everything")

    resp = client.post(f"/api/ideas/{idea_id}/replan", headers=auth_headers(token))
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


def test_documents_requires_analyzed_status(client, monkeypatch):
    token = register_and_login(client, email="doc409@test.com")
    resp = client.post(
        "/api/ideas", json={"title": "T", "description": "D"}, headers=auth_headers(token)
    )
    idea_id = resp.json()["idea_id"]
    resp = client.post(
        f"/api/ideas/{idea_id}/documents",
        json={"doc_type": "synopsis"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409


def test_all_three_document_types_generate_and_persist(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.ideas.run_docs_agent",
        lambda doc_type, *a, **k: f"# {doc_type}\n\nfake generated content",
    )
    token, idea_id = analyzed_idea(client, monkeypatch, email="docs@test.com")

    for doc_type in ("synopsis", "methodology", "progress_report"):
        resp = client.post(
            f"/api/ideas/{idea_id}/documents",
            json={"doc_type": doc_type},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["doc_type"] == doc_type

    docs = client.get(f"/api/ideas/{idea_id}/documents", headers=auth_headers(token)).json()
    assert len(docs) == 3
    assert {d["doc_type"] for d in docs} == {"synopsis", "methodology", "progress_report"}


def test_invalid_doc_type_rejected(client, monkeypatch):
    token, idea_id = analyzed_idea(client, monkeypatch, email="baddoc@test.com")
    resp = client.post(
        f"/api/ideas/{idea_id}/documents",
        json={"doc_type": "abstract"},  # not one of the 3 known types
        headers=auth_headers(token),
    )
    assert resp.status_code == 422
