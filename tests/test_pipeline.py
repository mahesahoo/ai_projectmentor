"""Milestone 4 checklist step 14 - pipeline routing/persistence/status-
transition tests. All 5 pipeline-stage agent calls are mocked at the
app.agents.pipeline module boundary (that module imports each
run_*_agent function directly into its own namespace, so patching
app.agents.feasibility.run_feasibility_agent etc. would NOT take effect -
pipeline.py already holds its own reference bound at import time).

TestClient blocks until the full ASGI cycle - including the BackgroundTask
that runs the pipeline - completes, so no polling loop is needed here the
way the manual browser-based rehearsals needed one: by the time
client.post("/ideas", ...) returns, the (mocked, instant) pipeline has
already finished.
"""
from app.schemas import (
    FeasibilityAgentOutput,
    RiskAgentOutput,
    RiskItem,
    ScopeAgentOutput,
    TechAgentOutput,
    TechStackItem,
    TimelineAgentOutput,
    WeekPlan,
)
from tests.conftest import auth_headers, register_and_login

FAKE_FEASIBILITY = FeasibilityAgentOutput(verdict="feasible", reasoning="Well-scoped for a term.")
FAKE_NOT_FEASIBLE = FeasibilityAgentOutput(verdict="not_feasible", reasoning="Scope is undefined.")
FAKE_SCOPE = ScopeAgentOutput(
    objectives=["Build the core feature"],
    deliverables=["A working web app"],
    out_of_scope=["Mobile app"],
)
FAKE_TECH = TechAgentOutput(
    stack=[TechStackItem(category="backend", technology="FastAPI", reasoning="known")],
    reasoning="Simple, well-supported stack.",
)
FAKE_TIMELINE = TimelineAgentOutput(
    weeks=[WeekPlan(week=1, tasks=["Scaffold"]), WeekPlan(week=2, tasks=["Core feature"])]
)
FAKE_RISK = RiskAgentOutput(
    risks=[RiskItem(risk="Scope creep", likelihood="medium", mitigation="Timebox features")]
)


def _patch_full_pipeline(monkeypatch):
    monkeypatch.setattr(
        "app.agents.pipeline.run_feasibility_agent", lambda *a, **k: FAKE_FEASIBILITY
    )
    monkeypatch.setattr("app.agents.pipeline.run_scope_agent", lambda *a, **k: FAKE_SCOPE)
    monkeypatch.setattr("app.agents.pipeline.run_tech_agent", lambda *a, **k: FAKE_TECH)
    monkeypatch.setattr("app.agents.pipeline.run_timeline_agent", lambda *a, **k: FAKE_TIMELINE)
    monkeypatch.setattr("app.agents.pipeline.run_risk_agent", lambda *a, **k: FAKE_RISK)


def submit_idea(client, token, title="Test Idea", description="A reasonably scoped test project idea."):
    resp = client.post(
        "/api/ideas",
        json={"title": title, "description": description},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["idea_id"]


def test_full_pipeline_reaches_analyzed_with_all_five_sections(client, monkeypatch):
    _patch_full_pipeline(monkeypatch)
    token = register_and_login(client)
    idea_id = submit_idea(client, token)

    resp = client.get(f"/api/ideas/{idea_id}", headers=auth_headers(token))
    assert resp.json()["status"] == "analyzed"

    bp = client.get(f"/api/ideas/{idea_id}/blueprint", headers=auth_headers(token)).json()
    assert bp["feasibility"]["verdict"] == "feasible"
    assert bp["scope"]["objectives"] == ["Build the core feature"]
    assert bp["tech"]["stack"][0]["technology"] == "FastAPI"
    assert len(bp["timeline"]["weeks"]) == 2
    assert bp["risk"]["risks"][0]["likelihood"] == "medium"


def test_not_feasible_idea_stops_pipeline_early(client, monkeypatch):
    monkeypatch.setattr(
        "app.agents.pipeline.run_feasibility_agent", lambda *a, **k: FAKE_NOT_FEASIBLE
    )
    # Deliberately do NOT patch scope/tech/timeline/risk - if the pipeline
    # tried to call them, it would hit the real (placeholder-keyed) Gemini
    # client and fail loudly, which is exactly the regression this guards.
    token = register_and_login(client, email="vague@test.com")
    idea_id = submit_idea(client, token, title="App", description="do everything")

    resp = client.get(f"/api/ideas/{idea_id}", headers=auth_headers(token))
    assert resp.json()["status"] == "analyzed"

    bp = client.get(f"/api/ideas/{idea_id}/blueprint", headers=auth_headers(token)).json()
    assert bp["feasibility"]["verdict"] == "not_feasible"
    assert bp["scope"] is None
    assert bp["tech"] is None
    assert bp["timeline"] is None
    assert bp["risk"] is None


def test_agent_exception_sets_status_failed(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("simulated Gemini failure")

    monkeypatch.setattr("app.agents.pipeline.run_feasibility_agent", boom)
    token = register_and_login(client, email="fail@test.com")
    idea_id = submit_idea(client, token)

    resp = client.get(f"/api/ideas/{idea_id}", headers=auth_headers(token))
    assert resp.json()["status"] == "failed"


def test_idea_isolation_between_students(client, monkeypatch):
    _patch_full_pipeline(monkeypatch)
    token_a = register_and_login(client, email="a@test.com")
    token_b = register_and_login(client, email="b@test.com")
    idea_id = submit_idea(client, token_a)

    # Student B can't see student A's idea
    resp = client.get(f"/api/ideas/{idea_id}", headers=auth_headers(token_b))
    assert resp.status_code == 404
