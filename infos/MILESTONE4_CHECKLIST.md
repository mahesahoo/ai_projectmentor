# Milestone 4 — Step-by-Step Checklist

Source references for this checklist:
- `infos/mil4.jpeg` — Milestone 4 brief (Week 7–8, ~10 hours): faculty monitoring dashboard,
  end-to-end testing across all agents/workflows, prompt/pipeline optimization, final
  documentation + demonstration.
- `infos/MILESTONE2_CHECKLIST.md` / `infos/MILESTONE3_CHECKLIST.md` — the pattern this milestone
  extends (sequential agent chain, lazy Gemini client, audit-trail persistence, explicit-action
  gating over automatic reruns).
- `README.md` / `app/` — existing FastAPI app this milestone extends (not a new project).

Decisions locked in for this build (defaults — flag if any should change before starting):
- **Faculty access: one `is_faculty` boolean on `Student`, not a new user type.** Not "no auth"
  (an unauthenticated cross-student data endpoint has no business existing in a project that gets
  presented), and not a separate registration/RBAC system either (real scope creep for ~10 hours,
  and the brief never mentions faculty accounts). The middle option reuses the JWT machinery
  already in `app/auth.py` almost verbatim: a `get_current_faculty` dependency alongside the
  existing `get_current_student` (same pattern, checks `student.is_faculty` instead of just
  decoding the token) is on the order of 15 lines, not a build-out. Confirm the exact line count
  against `app/auth.py:37` when writing it, but this is the default — no more "open question."
- **Health indicators are computed, not generated.** Verdict, weeks-completed-vs-total,
  high-risk count, replan count, days-since-last-progress-update, chat message count — all
  derivable directly from existing tables with plain SQL/Python, zero LLM calls. Keep it that way;
  don't burn API quota computing something a `COUNT()` already answers.
- **The "auto-generated mentor summary" is the one new agent this milestone adds** — a 9th agent,
  same lazy-client / `response_json_schema` pattern as the other 8, one call per project, called
  on-demand from the dashboard (not automatically re-run on every dashboard load — same
  cost-discipline reasoning as M3's explicit replan).
- **End-to-end testing means a real automated suite**, not more ad-hoc curl/bash scripts. This
  session's own M2/M3 rehearsals repeatedly hit friction that a real test suite would have caught
  immediately (wrong field names, wrong URLs, a broken venv) — `pytest` + FastAPI's `TestClient`
  goes in `requirements.txt` for the first time this milestone.
- **Most tests mock the `run_*_agent` calls; exactly one is a real Gemini smoke test.** The suite
  as a literal reading of the brief (exercise every agent for real, every time) would make 30-40
  live API calls per run — minutes of wall time on a free-tier key, non-deterministic, and this
  session already hit one transient `503` mid-rehearsal. A suite that flakes is a suite nobody
  runs. Default: patch the `run_*_agent` functions at the module boundary (`_call_agent`'s
  indirection in `app/routers/ideas.py` makes this a clean seam) for all workflow/routing/
  persistence tests, and keep one `@pytest.mark.live` test, deselected by default, that proves
  the real Gemini wiring still works end-to-end.
- Same core stack as M2/M3 otherwise: raw `google-genai` SDK, `gemini-3.5-flash`, no agent
  framework, no new top-level folder for the app itself (tests get their own `tests/` folder).

---

## 0. Environment setup

1. Add `pytest` (and `httpx`, which FastAPI's `TestClient` needs) to `requirements.txt`;
   `pip install -r requirements.txt` to pick them up. Confirm `GEMINI_API_KEY` is still set for
   any test that exercises a real agent call.
   *Why:* first milestone that needs a dependency beyond the running app itself.
2. **Fix confirmed this session:** `venv/bin/*`'s console-script shebangs were pointing at a
   stale pre-reorg path and silently broke `pip`/`uvicorn`/etc. Already fixed and pushed
   (commit `d5d1a7c`) — just confirm `source venv/bin/activate && uvicorn --version` still
   resolves cleanly before starting M4 work, since a broken `pip` would block step 1 above.

## 1. Data model — 1 new table, 1 new agent-output shape

3. **`ProjectSummary`** (`app/models.py`) — mirrors the other agent-output tables: `idea_id` FK,
   PK, `summary` (text), `health_status` (`"on_track"` / `"at_risk"` / `"stalled"` / `"not_feasible"`),
   `created_at`. Same audit-trail pattern — new row per generation, `latest()` picks the newest.
   *Why a DB row at all, if it's dashboard-only:* so re-opening the dashboard doesn't force a
   re-generation (and re-billing) of every project's summary on every page load.
4. **Add `ProjectSummaryOut` schema** to `app/schemas.py`, plus a `DashboardProjectOut` (or similar)
   response shape combining one idea + its computed health indicators + its latest summary (if any)
   — this is the shape the dashboard endpoint actually returns, one row per idea.

## 2. Build the two new pieces

5. **Faculty Summary Agent** (`app/agents/faculty_summary.py`)
   - Input: the full blueprint (feasibility/scope/tech/timeline/risk) + progress-update history +
     replan count + chat message count.
   - Output: structured `{summary: str, health_status: Literal[...]}` via `response_json_schema`
     (same pattern as Risk Agent) — a short paragraph a faculty member can read in 10 seconds,
     plus a machine-usable status tag for sorting/filtering on the dashboard.
   - System prompt should explicitly instruct against restating the blueprint verbatim — the
     value is synthesis ("on track but slipping on Week 4's file-upload blocker"), not a summary
     of a summary.
   *Why last new agent, not first:* it's the only piece of M4 that depends on everything else
   (blueprint + progress + chat + replan history) already existing, which it does as of M3.

6. **Health-indicator computation** (`app/routers/faculty.py` or inline in the dashboard endpoint)
   - Per idea: `verdict`, `weeks_completed / weeks_total`, `high_risk_count` (from latest
     `RiskAssessment`), `replan_count`, `days_since_last_progress` (from latest
     `ProgressUpdate.created_at`), `chat_message_count`.
   - **`weeks_completed` source — do NOT string-sniff the timeline.** `TimelinePlan.weeks` is
     `{"week": N, "tasks": [...]}` — after a replan, some `tasks` strings happen to start with
     "Completed:" because that's how the replan agent's *prose* reads, not a structured field; the
     original (pre-replan) timeline has no such marker at all, so sniffing for it reads 0/N
     "completed" for every project that hasn't replanned yet — which is most of them. Use
     `max(ProgressUpdate.week_number)` instead: it's structured, student-supplied, exists without
     requiring a replan first, and matches what "weeks completed" actually means to a faculty
     reader (confirmed via the M3 rehearsal transcript, where this exact string-sniffing attempt
     returned `?` for all 8 weeks).
   - `replan_count` via `COUNT(TimelinePlan) - 1` is fine on the happy path, but note honestly: the
     `_call_agent` wrapper added in M3 means a replan can commit the new `TimelinePlan` and then
     fail before committing the paired `RiskAssessment` (if Gemini errors between the two calls) —
     so `TimelinePlan` and `RiskAssessment` row counts can diverge after a failed retry. Not worth
     a schema change to fix; just don't present `replan_count` as more precisely synced with the
     risk history than it actually is.
   - Pure Python/SQL over existing tables — no LLM call, no new persistence needed (computed fresh
     on every dashboard request, since it's cheap).

## 3. API surface

All three routes below are gated on the new `get_current_faculty` dependency (step "Faculty
access" above), not `get_current_student` — this is the one router in the app that deliberately
crosses student boundaries, so it needs its own auth check rather than reusing the ownership
pattern (`_get_owned_idea`) everywhere else.

7. **`GET /api/faculty/dashboard`** — list of every student's every idea with computed health
   indicators + latest `ProjectSummary` if one exists (don't auto-generate on this call — see
   decision above).
8. **`POST /api/faculty/ideas/{id}/summary`** — explicit trigger to (re)generate that one idea's
   `ProjectSummary`. Mirrors M3's `POST /replan` pattern: cheap to view, costly action stays a
   separate, deliberate call.
9. **`GET /api/faculty/ideas/{id}`** — single-idea detail view (full blueprint + progress + chat
   history + summary), for when a faculty member clicks into one project from the dashboard list.

## 4. Frontend

10. **New dashboard view** (`frontend/index.html`, new route e.g. `/faculty.html` served the same
    SPA way as the other routes) — a table/card list of all projects with status pill, health
    badge (color-coded like M3's risk-likelihood badges), and a "Generate summary" button per row
    that calls the summary endpoint and displays the result inline.
11. **Detail drill-down** — clicking a project opens the same blueprint-modal pattern already
    built for students, extended with the progress/chat history already rendered there, plus the
    summary text.

## 5. End-to-end automated test suite (`tests/`)

12. **`tests/conftest.py`** — a `TestClient` fixture wired to a throwaway SQLite file (or
    `sqlite:///:memory:` with `StaticPool`, if that plays nicely with FastAPI's threaded
    `TestClient` — verify; decide during this step, not before). **Must explicitly override
    `app.dependency_overrides[get_db]`** — `app/database.py` resolves `DATABASE_URL` at import
    time, so a `TestClient` built without the override will happily read/write the real
    `project_mentor.db` on disk. This matters more than the memory-vs-tempfile choice.
13. **`tests/test_auth.py`** — register, duplicate-email rejection, login, wrong-password
    rejection, auth-required routes reject without a token. (Formalizes what M1's manual "Tested"
    section already covered by hand.) No agent calls involved — nothing to mock here.
14. **`tests/test_pipeline.py`**, **`tests/test_m3_features.py`**, **`tests/test_faculty_dashboard.py`**
    — cover the same ground as originally scoped (full pipeline + `not_feasible` early-stop, chat
    memory + progress/replan + all 3 doc types + `409` gating, dashboard aggregation + summary
    persistence + health-indicator correctness against fixture data) — **but with every
    `run_*_agent` call patched at the module boundary** (`app/routers/ideas.py`'s `_call_agent`
    indirection makes this a clean seam: `monkeypatch.setattr("app.routers.ideas.run_mentor_agent",
    fake_fn)` etc.) to return canned, schema-valid fixture output instead of calling Gemini. A
    literal reading of "test every agent for real" would mean ~30-40 live calls per full run —
    minutes of wall time on a free-tier key, non-deterministic, and this session's own M3
    rehearsal already ate one transient `503` mid-run. Mocked tests check routing, persistence,
    status transitions, and gating logic — the actual product logic — deterministically and fast.
15. **`tests/test_live_smoke.py`**, marked `@pytest.mark.live`, deselected by default (configure
    in `pytest.ini`/`pyproject.toml`: `addopts = -m "not live"`) — exactly one real submit-and-wait
    against the live Gemini API, run manually or in CI on a schedule, proving the actual wiring
    (not just the mocks) still works.
    *Why formal tests now, not more manual rehearsals:* the M2 and M3 rehearsals this session both
    caught real bugs (a stale venv, a bare 500 on transient errors) precisely because they were
    thorough — a pytest suite makes that thoroughness repeatable in seconds instead of a 30-minute
    manual walkthrough before every future change, as long as it's fast enough to actually get run.

## 6. Prompt quality / pipeline reliability pass

16. **Re-read all 9 system prompts** (`app/agents/*.py`) back-to-back in one sitting — look for:
    inconsistent tone/persona across agents, any prompt that's vague enough to produce generic
    output (the exact failure mode M2/M3's design already guards against explicitly — verify it
    actually holds under a second look), and token-budget mismatches (`max_output_tokens` too low
    for a prompt that asks for a lot, or too high for one that doesn't).
17. **Confirm Gemini SDK retry behavior** — `google-genai`'s bundled `tenacity` already retries
    transient errors before they reach app code (confirmed during M3 rehearsal: a `503` still
    surfaced after retries were exhausted, meaning retries happened first). Don't add a second,
    redundant retry layer on top — but do confirm the retry count/backoff is reasonable for a
    live demo (a 30-second silent retry before failing is worse on stage than failing fast with
    the clean `503` message M3 already added).
18. **Spot-check structured-output reliability** — run each `response_json_schema`-constrained
    agent (Feasibility, Scope, Tech, Timeline, Risk, Replan, and the new Faculty Summary agent)
    a handful of times against varied inputs; confirm none silently produce malformed/truncated
    JSON that Pydantic would reject with an unhelpful error.

## 7. Final documentation + demonstration

19. **Add a "Milestone 4 status" section to `README.md`** (same pattern as M1–M3 sections), plus
    the new `/api/faculty/*` rows in the endpoint table and `faculty_summary.py`/`faculty.py` in
    the project structure tree.
20. **Project report** — a more formal end-of-project document (`PROJECT_REPORT.md` or similar)
    covering the full 4-milestone arc: architecture, all 9 agents, data model, key design
    decisions and their rationale (audit-trail persistence, explicit-action gating, lazy client
    init, structured vs. plain-text output), validation approach, and what M5+ (if any) would be.
    *Why separate from the README:* the README is a working reference for someone running the
    app; the project report is a narrative document for someone grading the project who won't run
    it at all.
21. **Presentation deliverables**, matching the M1–M3 pattern exactly: `Milestone4_Presentation.pptx`
    (built the same way — copy the previous deck, swap placeholder text via python-pptx, preserve
    theme) and `PRESENTATION_SCRIPT_M4.md` (same runbook format — 🖥️/✅/🗣️ per section, a live
    demo section, Q&A prep). This is the "final demonstration" deliverable from the brief.
22. **Full rehearsal run** before the actual presentation — same process as M2/M3: isolated
    server + DB, walk every claim in the script against real behavior, including the new
    dashboard and the automated test suite actually passing (`pytest` output as part of the
    validation evidence, not just a claim).

---

## Open questions worth deciding before/while building (not yet locked in)

- **In-memory vs. file-based SQLite for tests:** `:memory:` is faster and self-cleaning but needs
  `StaticPool`/`check_same_thread=False` wiring to work with FastAPI's `TestClient`; a throwaway
  temp file is more foolproof if that wiring turns out finicky. Decide during step 12 — the
  `get_db` override matters more than which SQLite mode backs it either way.
- **Faculty account provisioning:** with `is_faculty` as a plain boolean column, how does anyone
  actually become faculty — a one-off manual DB flip for the demo account, a protected
  admin-only endpoint, or a seed script? A manual flip is enough for a milestone demo; don't build
  a faculty-provisioning UI nobody asked for.

## After completion

- Commit and push once the checklist above is fully worked through and validated — same rhythm as
  M2/M3 (build → validate live → update docs → presentation deliverables → rehearse → commit/push).
- This is the last milestone per the brief (`infos/mil4.jpeg` doesn't reference a Milestone 5) —
  the project report from step 20 should read as a genuine conclusion, not "to be continued."
