# Milestone 2 — Step-by-Step Checklist

Source references for this checklist:
- `infos/milestone2.txt` — official Milestone 2 task brief (5 tasks: Feasibility, Scope, Tech Recommendation, Timeline, Validation)
- `infos/AI Academic Project Mentor.docx` — full project statement, modules, and milestone-by-milestone outcomes
- `project-mentor/README.md` — current app structure, API endpoints, and the M1 → M2 handoff note on `ProjectIdea.status`
- `project-mentor/app/` — existing FastAPI app this milestone extends (not a new project)

Decisions locked in for this build:
- Raw Google Gemini SDK (`google-genai`, no agent framework), kept simple — switched from
  the Anthropic SDK originally planned, to avoid requiring a paid API key
- Model: `gemini-3.5-flash` for all four agents (Gemini free tier)
- Structured output via `response_json_schema` on `GenerateContentConfig`, parsed with
  `<Schema>.model_validate_json(response.text)` — not free-text parsing
- Same codebase as Milestone 1 — no new top-level folder for code (code lives in `project-mentor/`, the folder formerly named `milestone1/`)

---

## 0. Environment setup

1. **Add `google-genai` to `requirements.txt`** and `pip install google-genai` in the venv.
   *Why:* not currently a dependency — M1 had no LLM calls at all. (Originally planned as `anthropic`; switched to Gemini's free tier so validation testing doesn't require a paid account.)

2. **Set `GEMINI_API_KEY`** as an env var (same convention as `DATABASE_URL` in the README) — never hardcoded. Get a free key at https://aistudio.google.com/apikey.
   *Why:* the SDK reads it automatically; hardcoding would leak a secret into the repo.

3. **Create `app/agents/__init__.py` and `app/agents/client.py`** with a lazily-initialized `genai.Client()`, exposed via a `get_client()` accessor rather than a module-level instance.
   *Why:* unlike `anthropic.Anthropic()`, `genai.Client()` raises immediately at construction if no key is set — building it at import time would crash the whole app (including Milestone 1 routes that need no LLM) just because the key isn't configured. Lazy init defers that failure to actual agent use.

## 1. Data model — one table per agent

4. **Add 4 new SQLAlchemy models to `app/models.py`**: `FeasibilityReport`, `ScopeDefinition`, `TechRecommendation`, `TimelinePlan` — each with `idea_id` FK to `project_ideas.idea_id`, a PK, agent-specific fields, and `created_at`.
   *Why:* mirrors the existing `SkillAssessment`/`ProjectIdea` pattern (`app/models.py`), keeps M2 consistent with the Task 2 ER-diagram style, and gives every agent's output an audit trail instead of overwriting a single blob.

5. **Add matching Pydantic schemas to `app/schemas.py`** (`*In`/`*Out` pairs) — these double as the `response_json_schema` JSON schemas the agents must return.
   *Why:* one schema does two jobs — API response validation *and* the contract that constrains the LLM's output, so the agent can't return a shape the DB can't store.

6. **Run the app once to let `Base.metadata.create_all()` create the new tables** (`app/main.py`).
   *Why:* M1 already wired auto-create-on-startup for SQLite; no migration tooling exists yet.

## 2. Agent status model

7. **Widen `ProjectIdea.status` transitions**: `submitted → analyzing_feasibility → analyzing_scope → analyzing_tech → analyzing_timeline → analyzed`, plus a `failed` state.
   *Why:* the current docstring in `app/models.py` only anticipates one flip to `"analyzed"` — four sequential agents need enough granularity for progress display and failure attribution.

## 3. Build agents one at a time (in task order)

Build and manually verify each agent before starting the next — Scope/Tech/Timeline all depend on the *real* shape of the prior stage's output, not a guess at it.

8. **Feasibility Agent** (`app/agents/feasibility.py`)
   - System prompt: what makes an academic project feasible/risky/infeasible.
   - `get_client().models.generate_content(model="gemini-3.5-flash", config=types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=FeasibilityAgentOutput.model_json_schema()), ...)`.
   - Persist to `feasibility_reports`, flip `idea.status`.
   *Why first:* it's the pipeline's gate — simplest single-input call, establishes the request/response/persist pattern the other three copy.

9. **Scope Definition Agent** (`app/agents/scope.py`)
   - Input: idea + feasibility verdict/reasoning.
   - Output: objectives, deliverables, out-of-scope.
   *Why it needs feasibility's output:* scoping a project flagged "risky" should differ from scoping a clean "feasible" one — that's why these run in sequence, not parallel.

10. **Technology Recommendation Agent** (`app/agents/tech.py`)
    - Input: idea + scope + the student's `SkillAssessment` rows.
    *Why pull in skills:* the only place in the app where M1's skill-assessment data actually gets used — without it, "recommend a tech stack" can't weight toward what the student already knows.

11. **Timeline Planning Agent** (`app/agents/timeline.py`)
    - Input: idea + scope + tech stack.
    - Output: week-wise plan (JSON array of `{week, tasks}`).
    *Why last:* a timeline is meaningless without knowing what's being built (scope) and with what (tech stack).

## 4. Orchestration

12. **Write `app/agents/pipeline.py::run_pipeline(idea_id, db)`** — calls the four agents sequentially, catches broad `Exception` around the whole run (not a provider-specific error type), sets `idea.status = "failed"` on error instead of raising silently inside a background task. Deliberately broad: this runs unsupervised as a `BackgroundTask`, so nothing else will ever see an exception it doesn't handle itself — that includes Gemini API errors, but also e.g. a missing/invalid `GEMINI_API_KEY`, which `genai.Client()` raises as a plain `ValueError`/`TypeError`, not an API error type.
    *Why one orchestrator function:* keeps each agent pure/testable (input → output) and centralizes all status-transition logic instead of scattering it across 4 files.

13. **Replace `trigger_agent_pipeline_placeholder` in `app/routers/ideas.py`** with a call to `run_pipeline`, still fired via the existing `BackgroundTasks.add_task(...)`.
    *Why:* this is the exact hook M1 built for this purpose — the docstring says so directly. No new trigger mechanism needed.

## 5. API surface

14. **Add `GET /api/ideas/{id}/blueprint`** to `app/routers/ideas.py` — joins all 4 agent tables for one idea and returns them together.
    *Why:* the frontend needs one call to render the full blueprint rather than 4 separate polling requests.

## 6. Validation (Task 5 in `infos/milestone2.txt`)

15. **Manually run 3–5 varied sample project ideas** end-to-end through `POST /api/ideas` and confirm: status transitions fire correctly at each stage, each agent's output is coherent given the previous stage's output, and a deliberately bad/vague idea produces a sensible "infeasible" verdict rather than a hallucinated pass.
    *Why required, not optional:* `infos/milestone2.txt` names this as Task 5 explicitly — the deliverable isn't "the agents exist," it's "the pipeline works correctly across multiple inputs."

16. **Spot-check token/cost usage** (`response.usage`) on a couple of runs.
    *Why:* four sequential Opus calls per idea adds up during repeated manual testing — worth knowing early.

---

## After completion

- Add a "Milestone 2 status" section to `project-mentor/README.md` (same pattern as the existing "Milestone 1 status" section).
- Add `project-mentor/Milestone2_Presentation.pptx` and `project-mentor/PRESENTATION_SCRIPT_M2.md` for the presentation deliverable, once there's something real to present.
