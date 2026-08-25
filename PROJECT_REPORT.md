# AI Academic Project Mentor — Project Report

**A 4-milestone academic project.** This report is a narrative account of what was
built, why it was built that way, and how it was validated — written for someone
evaluating the finished project, not running it. For setup/usage instructions, see
`README.md`; for the milestone-by-milestone build process, see
`infos/MILESTONE{2,3,4}_CHECKLIST.md`.

---

## 1. Executive summary

AI Academic Project Mentor is a platform that takes a student's rough, two-line
project idea and turns it into a complete academic project plan — feasibility
verdict, scope, recommended tech stack, week-by-week timeline, and risk
assessment — using a sequential pipeline of Gemini-backed agents. From there, it
stays useful through execution: a conversational mentor grounded in that specific
plan, progress logging with on-demand replanning, and generated documentation
(synopsis, methodology, progress report). A faculty dashboard gives a mentor a
health-at-a-glance view across every student's project, with an AI-generated
summary and status tag per project, computed on demand.

The whole system — 9 LLM agents, 12 database tables, a FastAPI backend, and a
single-file vanilla-JS frontend — was built across 4 milestones and is fully
functional end to end, with both extensive manual live-API validation and (from
Milestone 4 onward) an automated test suite.

## 2. Problem statement

Students starting an academic project typically get one thing from a mentor: a
single conversation at the start. After that, they're on their own to interpret
vague feedback, guess at scope, and self-report progress into a void. This
project's premise is that an LLM-backed "mentor" can do more than generate a
one-shot plan — it can stay grounded in that specific plan across an entire
project's lifecycle, and a faculty member overseeing many students at once needs
a way to see project health without reading every conversation transcript
themselves.

## 3. System architecture

```
Browser  ──►  FastAPI app (single process)  ──►  SQLite / PostgreSQL
                    │
                    └──►  Gemini API (gemini-3.5-flash, 9 agents)
```

- **Backend:** FastAPI, serving both the JSON API (`/api/*`) and the frontend's
  static files from the same process — no CORS, no separate frontend server.
- **Database:** SQLAlchemy ORM, SQLite by default, PostgreSQL-ready via a single
  `DATABASE_URL` environment variable (no code changes either way).
- **Auth:** JWT, 24-hour expiry, `passlib`/`pbkdf2_sha256` password hashing.
  Faculty access is an `is_faculty` boolean on the same `Student` table, not a
  separate account type (§6.1).
- **LLM layer:** the raw `google-genai` SDK against `gemini-3.5-flash` (Gemini's
  free tier) — no agent framework. Each agent is a plain Python function: build a
  prompt, call `generate_content`, parse the result. Structured-output agents
  constrain the response with a Pydantic-derived JSON schema
  (`response_json_schema`); conversational/document agents get plain text.
- **Frontend:** one HTML file (`frontend/index.html`), vanilla JS, no build step,
  no framework. Client-side routing renders the right view per URL path.

## 4. The agent pipeline — all 9 agents

| # | Agent | Milestone | Input | Output | Trigger |
|---|---|---|---|---|---|
| 1 | Feasibility Analysis | M2 | Title + description | Verdict (`feasible`/`risky`/`not_feasible`) + reasoning | Pipeline stage 1 |
| 2 | Scope Definition | M2 | Idea + feasibility | Objectives, deliverables, out-of-scope | Pipeline stage 2 |
| 3 | Technology Recommendation | M2 | Idea + scope + student's `SkillAssessment` rows | Weighted tech stack + reasoning | Pipeline stage 3 |
| 4 | Timeline Planning | M2 | Idea + scope + stack | Week-by-week task list | Pipeline stage 4 |
| 5 | Risk Assessment & Mitigation | M3 | Full blueprint so far | Risks with likelihood + mitigation | Pipeline stage 5 |
| 6 | Conversational Mentor | M3 | Full blueprint + chat history + new message | Plain-text reply | `POST /chat`, synchronous |
| 7 | Replan (Timeline) | M3 | Original plan + progress log | Revised full timeline | `POST /replan` (also re-runs #5) |
| 8 | Documentation Generation | M3 | Full blueprint + progress | Markdown document | `POST /documents` |
| 9 | Faculty Summary | M4 | Full blueprint + progress + chat/replan counts | Short summary + health tag | `POST /faculty/.../summary` |

Agents 1–5 run automatically, chained, as a `BackgroundTask` right after idea
submission (`app/agents/pipeline.py`), advancing `ProjectIdea.status` through
`analyzing_feasibility → analyzing_scope → analyzing_tech → analyzing_timeline →
analyzing_risk → analyzed` — a status the frontend polls to show live progress. A
`not_feasible` verdict stops the pipeline immediately after stage 1: there's
nothing real to scope, recommend a stack for, or schedule.

Agents 6–9 are all explicit, on-demand actions triggered by a specific API call —
none of them re-run automatically. This is a deliberate, repeated pattern across
the whole build (§6.2).

## 5. Data model

12 tables, SQLAlchemy ORM, all UUID primary keys:

**Core:** `students`, `skill_assessments`, `project_ideas`.

**Agent-output tables** (one per agent, all foreign-keyed to `project_ideas`,
timestamped): `feasibility_reports`, `scope_definitions`, `tech_recommendations`,
`timeline_plans`, `risk_assessments`, `mentor_messages`, `progress_updates`,
`generated_documents`, `project_summaries`.

Every agent-output table follows the same audit-trail rule: **a new row per
generation, never an overwrite.** `GET /blueprint` (and the equivalent faculty
endpoints) always read the *latest* row per idea via a shared `_latest()` helper
(`max(rows, key=created_at)`). This means a replan doesn't destroy the original
plan, a regenerated document doesn't erase an earlier version, and a second
faculty summary doesn't overwrite the first — the full history is always still
in the database, even though the API surfaces only the newest by default.

## 6. Key design decisions

### 6.1 Faculty access: a boolean, not a new account type

The Milestone 4 brief asks for a "faculty monitoring dashboard," not a faculty
registration/login system. `Student.is_faculty` is a plain boolean column;
faculty routes are gated by a `get_current_faculty` dependency that wraps the
existing `get_current_student` JWT check and adds one condition. There is no
faculty sign-up flow — becoming faculty is a manual database flip for a demo
account. This was a deliberate call against building a second user type: it
would be real scope creep for a milestone budgeted at roughly 10 hours, and the
brief's own wording never implies one.

### 6.2 Explicit-action gating over automatic reruns

Every *costly* action in this app (replan, document generation, faculty summary
generation) is a separate, deliberate API call from the *free* action that makes
it relevant (logging progress, viewing the dashboard). Logging progress is a
plain database insert with zero LLM calls; triggering a replan that reads that
progress is a distinct button/endpoint. Viewing the faculty dashboard never
generates a summary; a faculty member has to explicitly ask for one. This
decouples "the student/faculty wants to record or see something" from "an LLM
call happens," so a chatty student or a faculty member browsing many projects
can't accidentally burn API quota just by using the app normally. This is a
documented, deliberate deviation from the Milestone 3 brief's literal wording
("progress updates trigger plan adjustments via the agent pipeline") — cost
predictability was judged more valuable than literal compliance with a brief
that doesn't specify a budget. The same deviation applies to the Milestone 4
brief's own wording — it asks for "auto-generated mentor summaries," and this
build generates them on explicit request instead, for the identical reason.

### 6.3 Lazy Gemini client construction

`app/agents/client.py`'s `get_client()` constructs the `google.genai.Client()`
on first use, not at module import time. `genai.Client()` raises immediately if
`GEMINI_API_KEY` isn't set — constructing it eagerly at import time would crash
the *entire app*, including the Milestone 1 routes (register/login/profile) that
need no LLM at all, just because the key isn't configured yet. Deferring
construction means the app always boots; only an actual agent call fails (and
fails gracefully — see §6.5) if the key is missing.

### 6.4 Structured vs. plain-text LLM output

Agents that produce a fixed shape (feasibility verdict, scope lists, tech stack,
timeline weeks, risks, replanned timeline, faculty summary + health tag) use
Pydantic-derived `response_json_schema` constraints — the same Pydantic model
serves double duty as both the API's response schema and the LLM's output
contract, eliminating a whole category of manual JSON-parsing/validation code.
Agents that produce genuinely free-form text — the mentor's chat replies, the
generated documents — get no schema at all; forcing a rigid shape onto a
conversational reply or a prose document would make the output read robotically
and serves no real validation purpose (there's no fixed set of fields a chat
reply or a synopsis document must have).

### 6.5 Graceful degradation and error handling

Two layers of failure handling, matched to two different execution contexts:

- The **background pipeline** (`run_pipeline`) wraps its entire execution in one
  broad `try/except`. Any failure — a bad key, a network error, a malformed
  response — sets `idea.status = "failed"` and stops, rather than leaving the
  idea stuck on an `analyzing_*` status forever or crashing the background
  worker silently.
- The **synchronous endpoints** (chat, replan, documents, faculty summary) go
  through a shared `_call_agent()` helper (`app/routers/ideas.py`) that catches
  any exception from the underlying agent call and converts it into a clean
  `503` with a JSON `{"detail": "..."}` body, instead of letting it bubble up
  as a bare, un-JSON'd `500 Internal Server Error`. This was added mid-build
  after live testing surfaced exactly that failure mode (a transient Gemini
  `503`), and later proved itself again against a *real* `429` quota-exhaustion
  error during Milestone 4 development — confirmed working against a genuine
  production failure, not just a simulated one.

Every downstream consumer of a possibly-missing blueprint section (chat,
documents, faculty summary, the frontend's rendering) uses the same
`if section else <fallback>` pattern rather than assuming a full blueprint
always exists — validated explicitly against a deliberately vague/infeasible
idea that stops after stage 1, leaving scope/tech/timeline/risk all `None`.

### 6.6 No automatic retry on Gemini API failures

`genai.Client()`, constructed with no explicit `http_options`, retries nothing —
traced directly in the SDK's own `_api_client.py`: the default retry
configuration is `stop_after_attempt(1)`, a single attempt. This was nearly
misdiagnosed as "the SDK already retries for us" earlier in the build (tenacity
stack frames appear in a traceback even for a single, non-retried attempt,
which looks superficially like a retry sequence), until traced through the
source directly. Once correctly understood, adding retry was considered and
declined: `429` (free-tier daily quota exhaustion — genuinely this project's
most common failure mode during heavy live-API testing) is on the SDK's own
retriable-status list, but retrying a quota-exhausted call cannot succeed. Doing
so would only add several seconds of silent delay before an identical failure —
strictly worse for a live demo than the fast, clean `503` this build already
returns.

## 7. Validation and testing approach

The project's testing approach evolved across milestones, deliberately:

- **Milestones 1–3:** extensive *manual* validation against the real, running
  application and the real Gemini API — registration/auth flows, the full
  5-agent pipeline on varied sample ideas (solid, vague, overambitious, a
  skill-weighting check), and a full continuous lifecycle walkthrough for
  Milestone 3 (pipeline → chat with confirmed memory → progress + replan →
  all 3 document types), including an edge-case run on a deliberately
  infeasible idea to confirm graceful degradation. Two full-length rehearsals
  (isolated server + database, walking every claim in the presentation scripts
  against real behavior) also caught real infrastructure bugs unrelated to the
  application logic itself — see §8.
- **Milestone 4:** formalized into an automated `pytest` suite (`tests/`) — 25
  tests that mock every `run_*_agent` call at the exact module boundary each
  caller imports from (patching the wrong module silently no-ops, since Python
  binds names at import time — a mistake this build's own design process caught
  before it shipped), covering routing, persistence, status transitions, and
  auth/ownership gating deterministically in under 10 seconds. Exactly one test
  is marked `@pytest.mark.live` and hits the real Gemini API, proving the actual
  agent wiring — prompts, schemas, the SDK client — still works end to end, not
  just the logic around it. Both run modes are documented in `README.md`.

This progression reflects a real judgment: manual, thorough, live-API validation
was the right tool while the system's shape was still changing rapidly across
three milestones; a fast, deterministic automated suite became the right tool
once there was a stable foundation worth protecting from regression as new
features (Milestone 4) were added on top of it.

## 8. Notable bugs found during development (and how)

A project report should be honest about what actually went wrong, not just what
was built. A representative sample, because each reflects a different kind of
verification that caught it:

- **A stale venv breaking the exact setup command in this project's own
  README/presentation scripts** — `venv/bin/uvicorn`, `pip`, and ~20 other
  console scripts had shebang lines pointing at a pre-reorg directory path that
  no longer existed. Found only by actually running the documented command
  during a presentation rehearsal, not by reading the scripts.
- **A token-budget bug specific to `gemini-3.5-flash`'s "thinking" tokens** —
  the Faculty Summary agent's initial `max_output_tokens=600` left almost no
  room for visible output once the model's internal reasoning tokens (measured
  at ~570 on one real call) were accounted for, truncating structured JSON
  mid-string. Found by running the agent against the live API immediately after
  writing it, not by code review.
- **A missing `status === "failed"` guard in the faculty detail view's
  frontend rendering** — would have shown "Still working — the Feasibility
  agent is running now…" for a pipeline that had actually crashed. Found only
  because a leftover failed idea from an unrelated earlier test happened to
  still be sitting in the dashboard during a routine verification pass.
- **A wrong assumption about SDK retry behavior**, carried in this project's
  own Milestone 4 planning checklist for one work session before being traced
  and corrected (§6.6) — a reminder that even a note written earlier in the
  same project's build process needs re-verification, not just trust.

## 9. Known limitations and possible future work

This is the final milestone per the project brief — there is no Milestone 5
planned — but a few limitations are worth recording honestly rather than
implying the system has none:

- **Chat context window** grows unbounded with conversation length; a very long
  mentor conversation would eventually approach the model's input token limit.
  Not a problem at the scale this was built and tested for.
- **Replan's two-agent-call design can partially fail**: if the Timeline call
  in `POST /replan` succeeds but the follow-up Risk call fails, a new
  `TimelinePlan` row is committed without a matching new `RiskAssessment` row —
  the audit trail is honest about what happened, but the two tables' row counts
  can diverge from what a fully-succeeded replan would produce.
- **Faculty provisioning is manual** (§6.1) — fine for a demo/grading account,
  not a real deployment's onboarding flow.
- **No production deployment configuration** (process manager, HTTPS
  termination, secrets management beyond environment variables) — out of scope
  for an academic milestone project, but the first thing a real deployment
  would need to add.

## 10. Conclusion

Across 4 milestones, this project grew from a foundational student-onboarding
app with no AI at all into a 9-agent system that plans, mentors, tracks, and
documents an academic project's full lifecycle, plus a faculty-facing view
across every student. The build was validated the same way throughout — against
the real running application and the real Gemini API, not just by inspection —
and that discipline caught genuine bugs at every stage, several of which are
recorded honestly in §8 rather than smoothed over. The result matches the
brief's stated scope for each milestone while documenting, rather than hiding,
every place a deliberate design choice diverges from the brief's literal
wording.
