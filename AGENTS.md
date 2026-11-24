# AGENTS.md — AI Academic Project Mentor

Read this first. This is a **team project**; get the history right before changing
anything.

## What / why
Turns a student's rough project idea into a full academic project blueprint —
feasibility, scope, tech stack, timeline, risks — then keeps mentoring through
execution: chat, progress-driven replanning, on-demand documentation, plus a
faculty dashboard that shows a mentor how every student is doing.

Academic coursework project, milestones 1–4 complete (treated as finished).
Repo: `github.com/mahesahoo/ai_projectmentor`.

## Authorship (important)
Built jointly with **Priyadarsini Manisha** (`@priyadarsinimanisha`), whose repo
this was forked from / contributed to. The portfolio site describes it as
"team-built" for that reason. **Do not describe this as solo work** — the README
has a Contributors table and reviewers check it.

## Stack
- **Backend:** FastAPI + SQLAlchemy (SQLite default, PostgreSQL-ready), JWT auth (24 h)
- **Frontend:** plain HTML/CSS/vanilla JS, no build step
- **LLM:** Gemini via `google-genai` (`gemini-3.5-flash`, free tier)
- **Agents:** `app/agents/` — pipeline (5 stages), mentor, replan, docs, faculty
  summary, plus `feasibility`, `scope`, `tech`, `timeline`, `risk`, `status`

## Run
```sh
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="..."     # every agent calls Gemini; no key = nothing works
uvicorn app.main:app
```
Deliberately **not** run with `--reload` (see README: `venv/` lives in the project
folder and the watcher churns). No deployment is configured — it runs locally.

## Hard rules
- **Never commit `.env`, `project_mentor.db`, or `server.log`** — all gitignored,
  keep it that way. No API keys anywhere in history.
- **The blueprint prompts are the product.** Changing one changes every downstream
  stage; run the milestone checklist in `infos/MILESTONE*_CHECKLIST.md` after edits.
- **Course artefacts stay** (`Milestone*_Presentation.pptx`, `PROJECT_REPORT.md`,
  `infos/`). They are evidence of process, not clutter — don't "clean them up".

## Gotchas
- Free-tier Gemini rate limits can make a 5-stage pipeline look broken; it's quota,
  not code.
- `app/auth.py` uses JWT with 24 h expiry — long demos need a re-login.
- Faculty role never grants access to another user's records; that invariant is
  documented in code comments. Don't relax it for convenience.

## Next
Nothing scheduled. If picked up again: deployment (Render/Fly) + a screenshot in
the README would make it easier for a stranger to evaluate.

## Feedback log
Append dated one-liners here. Don't rewrite past entries.
- 2026-11-24 — User considers it finished; don't add features unprompted.
- 2026-11-24 — Credit the co-author explicitly anywhere it is showcased.
