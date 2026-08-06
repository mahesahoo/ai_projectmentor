# Milestone 3 — Step-by-Step Checklist

Source references for this checklist:
- `infos/AI Academic Project Mentor.docx` — full project statement; Milestone 3 section (Week 5–6):
  Risk Assessment Agent, conversational mentor interaction, progress-driven plan adjustment,
  on-demand documentation generation.
- `infos/MILESTONE2_CHECKLIST.md` — the pattern this milestone extends (sequential agent chain,
  lazy Gemini client, schema-constrained structured output).
- `README.md` / `app/` — existing FastAPI app this milestone extends (not a new project).

Decisions locked in for this build (defaults — flag if any should change before starting):
- Same stack as M2: raw `google-genai` SDK, `gemini-3.5-flash`, `response_json_schema` for
  structured agents. No agent framework, no new top-level folder.
- **Risk Agent** is a 5th step appended to the existing sequential pipeline (Feasibility → Scope →
  Tech → Timeline → **Risk**) — same pattern as the other four, not a separate system.
- **Conversational mentor** and **progress tracking** are new, separate modules — they read the
  finished blueprint as context but do not re-run the M2 pipeline automatically. Re-planning is an
  explicit student action ("Request replan"), not a side effect of every chat message. This avoids
  silent, uncontrolled agent reruns burning API quota on every message.
- **Documentation generation** produces persisted Markdown text per document type, generated
  on-demand, not regenerated automatically.

---

## 0. Environment setup

1. No new dependencies expected — same `google-genai` SDK, same DB, same auth. Confirm
   `GEMINI_API_KEY` is still set before starting agent work.
   *Why:* M3 reuses the M2 client/config; only new models, schemas, routers, and agent files are added.

## 1. Data model — 4 new tables

2. **`RiskAssessment`** (`app/models.py`) — mirrors `TimelinePlan`: `idea_id` FK, PK, `risks` (JSON
   list of `{risk, likelihood, mitigation}`), `created_at`.
   *Why:* keeps the same one-table-per-agent-output pattern from M2 — full audit trail, not an
   overwritten blob.

3. **`MentorMessage`** (`app/models.py`) — `idea_id` FK, PK, `role` (`"student"`/`"mentor"`),
   `content` (text), `created_at`.
   *Why:* a flat message log is the simplest structure that supports a chat thread and full
   conversation history as LLM context — no need for a separate `Conversation` table when there's
   exactly one thread per idea.

4. **`ProgressUpdate`** (`app/models.py`) — `idea_id` FK, PK, `week_number` (int, nullable),
   `update_text`, `created_at`.
   *Why:* separate from `MentorMessage` — progress updates are structured status reports the
   student explicitly logs, not free-form chat, and are what the replan agent reads.

5. **`GeneratedDocument`** (`app/models.py`) — `idea_id` FK, PK, `doc_type`
   (`"synopsis"`/`"methodology"`/`"progress_report"`), `content` (Markdown text), `created_at`.
   *Why:* persisting generated docs means the student/faculty can view past versions instead of
   re-generating (and re-paying LLM cost) every time they open the page.

6. **Add matching Pydantic schemas to `app/schemas.py`** (`*In`/`*Out` pairs), same double-duty
   pattern as M2 — API validation and `response_json_schema` contract where the output is
   structured (Risk Agent, replan agent). Chat replies and generated docs are plain text, no schema
   needed for those two.

7. **Run the app once** to let `Base.metadata.create_all()` create the new tables.

## 2. Status model

8. **Insert `analyzing_risk` into `ProjectIdea.status`** between `analyzing_timeline` and
   `analyzed`: `... → analyzing_timeline → analyzing_risk → analyzed`.
   *Why:* Risk Agent becomes the real last step of the blueprint pipeline — `analyzed` should only
   mean "all 5 agents finished," matching the pattern already established in M2.

9. Chat, progress updates, and document generation do **not** use `ProjectIdea.status` — they only
   make sense once status is already `analyzed`. Gate those endpoints with a check
   (`if idea.status != "analyzed": 403/409`) rather than adding more status values for them.
   *Why:* those are post-blueprint interactions, not pipeline stages; conflating them with the
   pipeline status enum would make the enum meaningless for progress display.

## 3. Build agents/modules one at a time

10. **Risk Assessment Agent** (`app/agents/risk.py`)
    - Input: idea + scope + tech stack + timeline (the full blueprint so far).
    - Output: list of `{risk, likelihood, mitigation}`.
    - Wire into `app/agents/pipeline.py::run_pipeline` as step 5, same broad-exception/status-update
      pattern as the other four.
    *Why first:* it's a straight copy of the existing agent pattern — lowest-risk (no pun intended)
    place to start, and finishing it completes the "full blueprint" feature end-to-end.

11. **Conversational Mentor module** (`app/agents/mentor.py` + `POST /api/ideas/{id}/chat`)
    - Input: full blueprint + `MentorMessage` history (last N messages) + new student message.
    - Plain-text Gemini call (`response_mime_type` unset — no structured schema), system prompt
      establishes the mentor persona and instructs it to stay grounded in the actual blueprint.
    - Persist both the student message and the mentor reply as two `MentorMessage` rows.
    *Why plain text, not structured:* conversational replies don't have a fixed shape to validate
    against — forcing a schema here would make the mentor sound robotic.

12. **Progress tracking + replan** (`POST /api/ideas/{id}/progress` to log an update;
    `POST /api/ideas/{id}/replan` as the explicit re-planning trigger)
    - Logging progress: just inserts a `ProgressUpdate` row, no LLM call.
    - Replan: re-runs Timeline Agent (and Risk Agent if timeline materially changed) with the
      original blueprint + full `ProgressUpdate` history as extra context; persists new rows
      rather than overwriting old ones (same audit-trail pattern — `GET /blueprint` should return
      the *latest* of each, same `latest()` helper M2 already has in `app/routers/ideas.py`).
    *Why replan is separate from logging:* lets the student log "week 2: behind schedule" multiple
    times before deciding to actually trigger a costly LLM replan — decouples cheap writes from
    expensive agent calls.

13. **Documentation Generation module** (`app/agents/docs.py` +
    `POST /api/ideas/{id}/documents?type=synopsis|methodology|progress_report`)
    - Input: full blueprint (+ progress history for `progress_report` specifically).
    - Plain-text Markdown output from Gemini, persisted as a new `GeneratedDocument` row per
      generation (not overwritten — same audit-trail reasoning as everywhere else in this app).
    *Why on-demand, not automatic:* the brief says "on-demand generation" explicitly — don't burn
    API calls generating docs nobody asked to see yet.

## 4. API surface

14. **`GET /api/ideas/{id}/chat`** — return full `MentorMessage` history for the idea (for the
    frontend to render a chat thread on load).

15. **`GET /api/ideas/{id}/progress`** — return `ProgressUpdate` history.

16. **`GET /api/ideas/{id}/documents`** — return all `GeneratedDocument` rows (list, most recent
    per type or full history — decide based on whether old versions are worth keeping visible).

17. **Extend `GET /api/ideas/{id}/blueprint`** (`BlueprintOut` in `app/schemas.py`) to include the
    latest `RiskAssessment`, alongside the existing four.

## 5. Frontend

18. **Add a "Risks" section** to the existing blueprint modal (`frontend/index.html`) — same
    pattern as scope/tech/timeline sections already there.

19. **Add a simple chat panel** — message list + input box, calling `GET/POST /api/ideas/{id}/chat`.
    Reuse the polling pattern already built for blueprint status if messages need near-live updates,
    but a simple "send → append response" flow (no polling) is likely sufficient since chat is
    synchronous request/response, not a background task.

20. **Add a progress-log + "Request replan" UI** and a **documents panel** (dropdown of doc type +
    "Generate" button, list of previously generated docs).

## 6. Validation

21. **Manually run the full lifecycle** on 2–3 existing analyzed ideas: risk agent output is
    coherent given the blueprint, a chat exchange stays grounded in the actual project (not a
    hallucinated different one), a logged progress update + replan produces a *revised* timeline
    that reasonably accounts for the reported progress, and each document type reads like the
    named artifact (a synopsis reads like a synopsis, not a copy of the methodology).
    *Why required:* same reasoning as M2 Task 5 — the deliverable is "the pipeline works
    correctly," not "the endpoints exist."

---

## Open questions worth deciding before/while building (not yet locked in)

- **Chat context window:** full message history could grow unbounded token cost over a long
  conversation. Consider capping to last N messages once this becomes a real problem — not needed
  for a first pass with short demo conversations.
- **Replan scope:** should replanning ever cascade back into Scope/Tech (e.g. progress reveals the
  chosen tech stack isn't working), or is Timeline+Risk always sufficient? Default above is
  Timeline+Risk only, to keep the blast radius predictable.
- **Document types:** brief names synopsis, methodology, progress report specifically — confirm no
  others are expected (e.g. an abstract, a final report) before building the doc-type enum.

## After completion

- Add a "Milestone 3 status" section to `README.md` (same pattern as M1/M2 sections).
- Presentation deliverables once there's something real to present, matching the M1/M2 pattern
  (`Milestone3_Presentation.pptx`, `PRESENTATION_SCRIPT_M3.md`).
