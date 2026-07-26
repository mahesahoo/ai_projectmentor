# Milestone 2: Full Presentation Runbook (Say + Show + Do)

One document to follow start to finish — for every section: what to say
(verbatim), what to have on screen, and the exact clicks/commands to get
there. Pairs with `Milestone2_Presentation.pptx` for the slide visuals.

**The one honest gap, up front:** the frontend only shows a status pill on
the ideas list (`submitted` → `analyzing_feasibility` → ... →
`analyzed`/`failed`). There is no page that renders the actual agent output.
To show verdict/scope/tech stack/timeline content, you use `/docs` (Swagger
UI) and `GET /api/ideas/{id}/blueprint`. If asked, say so plainly — Task 5
was validation, not a results-page UI task.

---

## 0. Pre-Presentation Setup — do this 10-15 minutes before the mentor arrives

**Exact commands, in order:**

```bash
cd /home/mahesh/mics/project-mentor
source venv/bin/activate
export GEMINI_API_KEY="..."          # your real key
echo $GEMINI_API_KEY                  # confirm it printed, not empty
rm -f project_mentor.db               # start from a clean database
uvicorn app.main:app --reload
```

⚠️ **Order matters here.** If a server from an earlier session is already
running, stop it first (`Ctrl+C` in its terminal) *before* deleting
`project_mentor.db` — deleting the DB file out from under a live `--reload`
server corrupts its connection (registration/login start returning
`500 Internal Server Error` even though `/docs` still loads fine, since
`/docs` never touches the database). If this happens, the fix is just to
`Ctrl+C` and rerun `uvicorn app.main:app --reload` — it's a stale-connection
artifact, not a code bug, but it's an easy mistake to make while doing a
last-minute "let me reset the database" right before presenting.

Leave that terminal window running and visible — the `[feasibility]`,
`[scope]`, `[tech]`, `[timeline]` print lines from each agent (with token
counts) are your visible, live proof the pipeline is actually executing,
stage by stage, not a canned response.

**Then:**

1. **Do one full rehearsal run now**, before the mentor arrives: register a
   student, add 2 skill assessments, submit one idea, watch it reach
   `analyzed` (see §5 for the exact idea text and skills to use — use the
   same ones so this rehearsal doubles as your fallback data). This confirms
   the key works and you know the exact clicks.
2. **Wait a minute or two after the rehearsal** before presenting for real —
   Gemini's free tier has a requests-per-minute limit; don't run the
   rehearsal immediately back-to-back with the live demo.
3. Open two browser tabs: `http://localhost:8000` and
   `http://localhost:8000/docs`.
4. Open these files as editor tabs, in this exact order (this is the order
   you'll walk through them):
   `app/agents/feasibility.py` → `app/agents/scope.py` → `app/agents/tech.py`
   → `app/agents/timeline.py` → `app/agents/pipeline.py` → `app/models.py` →
   `app/routers/ideas.py`.
5. Open `Milestone2_Presentation.pptx`, ready in presentation mode on slide 1.

---

## 🎙️ Introduction: Welcome & Overview
**Time target:** 1 minute

**🖥️ What to show:** `Milestone2_Presentation.pptx`, slide 1 (title slide).
Present in fullscreen/presentation mode. Don't switch windows during this part.

**✅ Steps:** Just talk over the title slide — no clicking needed yet.

**🗣️ What to say:**
> "Good morning/afternoon, Sir/Ma'am. Today, I am presenting the completion
> of **Milestone 2** of my academic project: the **AI Academic Project
> Mentor** platform.
>
> Milestone 1 built the foundation — student onboarding, skill assessment,
> and idea submission, with no AI logic at all. Milestone 2 is where the
> actual intelligence goes in: the multi-agent pipeline that takes a
> student's rough 2-3 line idea and turns it into a complete project
> blueprint, automatically.
>
> Let's go through the completed tasks one by one."

Advance to slides 2 and 3 (Objectives, Deliverables) and talk through their
bullet points directly off the slide — you already wrote those bullets
yourself, so no separate script is needed here; just read the slide content
naturally rather than word-for-word.

---

## 📋 TASK 1: Feasibility Analysis Agent
**Time target:** 2 minutes

**🖥️ What to show:** editor tab `app/agents/feasibility.py`

**✅ Steps:**
1. Scroll to line 6 (`SYSTEM_PROMPT = """...`). Point at the three verdict
   bullets inside it (`feasible` / `risky` / `not_feasible`).
2. Scroll to line 22 (`def run_feasibility_agent(...)`). Point at line 29
   (`response_json_schema=FeasibilityAgentOutput.model_json_schema()`) —
   this is the line that forces the model to return exactly this shape.

**🗣️ What to say:**
> "For **Task 1**, I built the Feasibility Analysis Agent — the first stage
> of the pipeline. It takes the student's title and description and returns
> one of three verdicts: **feasible** — realistic scope for an academic
> term; **risky** — achievable, but with notable risks worth flagging; or
> **not feasible** — too broad, or lacking real technical substance.
>
> The system prompt is deliberately written to be an honest mentor, not a
> rubber stamp — a vague one-liner like 'an app that uses AI to help people'
> gets flagged, not waved through. I'll demo that live in a few minutes."

---

## 🎯 TASK 2: Scope Definition Agent
**Time target:** 2 minutes

**🖥️ What to show:** editor tab `app/agents/scope.py`

**✅ Steps:**
1. Scroll to line 6 (`SYSTEM_PROMPT`), point at the "risky → trim scope more
   aggressively" instruction.
2. Scroll to line 22 (`def run_scope_agent(...)`), point at the function
   signature — specifically the `feasibility_verdict` and
   `feasibility_reasoning` parameters — this is the "context chaining" proof.

**🗣️ What to say:**
> "For **Task 2**, the Scope Definition Agent takes the idea plus the
> Feasibility Agent's actual verdict and reasoning as context, and produces
> three things: specific objectives, concrete deliverables, and an explicit
> out-of-scope list.
>
> This is where the pipeline's sequential design matters — the Scope Agent
> doesn't just see the raw idea, it sees what the previous agent concluded.
> If the verdict was 'risky,' the prompt instructs it to trim scope more
> aggressively. That's context chaining, not four independent LLM calls."

---

## 🛠️ TASK 3: Technology Recommendation Agent
**Time target:** 3 minutes

**🖥️ What to show:** editor tab `app/agents/tech.py`

**✅ Steps:**
1. Scroll to line 8 (`SYSTEM_PROMPT`), point at the "weight recommendations
   toward technologies the student already has proficiency in" instruction.
2. Scroll to line 24 (`def run_tech_agent(...)`), point at the `skills`
   parameter — this reads Milestone 1's `SkillAssessment` table.
3. Say: "I'll prove this actually works, live, in a few minutes" — don't
   demo it yet, that happens in Task 5.

**🗣️ What to say:**
> "For **Task 3**, the Technology Recommendation Agent is the one that
> actually uses Milestone 1's skill assessment data — which, until this
> milestone, nothing in the app actually read.
>
> It takes the scope plus the student's self-reported skills and recommends
> a stack weighted toward what the student already knows. I validated this
> specifically: I gave a test student advanced React and Node.js skills, and
> explicitly no Django experience. The agent recommended Node.js and
> Express — and in its reasoning, it explicitly said it was 'eliminating the
> need to learn a new backend framework like Django.' That's not a
> coincidence; it's the skill-weighting instruction working as designed."

---

## 📅 TASK 4: Timeline Planning Agent
**Time target:** 2 minutes

**🖥️ What to show:** editor tab `app/agents/timeline.py`

**✅ Steps:**
1. Scroll to line 8 (`SYSTEM_PROMPT`), point at the "6-8 weeks... sequence
   tasks so dependencies make sense... final week reserved for testing"
   instructions.

**🗣️ What to say:**
> "For **Task 4**, the Timeline Planning Agent takes the scope and the
> recommended tech stack and produces a week-by-week execution plan —
> typically 6 to 8 weeks, with tasks sequenced so dependencies make sense,
> like not scheduling frontend integration before the backend API it depends
> on exists. The final week is always reserved for testing, polish, and
> documentation rather than new features."

---

## ⚙️ Orchestration: How the Four Agents Chain Together
**Time target:** 2 minutes

**🖥️ What to show:** editor tab `app/agents/pipeline.py`

**✅ Steps:**
1. Scroll to line 18 (`def run_pipeline(...)`). Point at lines 33, 54, 72,
   96, 113 — the `idea.status = status.ANALYZING_...` assignments — show
   that each stage updates status before running the next agent.
2. Scroll to line 45 (`if feasibility.verdict == "not_feasible":`). Read the
   comment above line 50 out loud — this is the early-exit gate, flag it now
   because you'll reference it again in the engineering highlight later.
3. Scroll to line 116 (`except Exception as exc:`). Point at the comment —
   explain this is deliberately broad because a background task has no
   caller to catch what it misses.

**🗣️ What to say:**
> "This is the orchestrator that chains the four agents together. Each stage
> persists its output and advances `idea.status` — `analyzing_feasibility`,
> `analyzing_scope`, `analyzing_tech`, `analyzing_timeline`, then `analyzed`
> — so the frontend can poll and show live progress.
>
> One design decision I want to flag now: if the Feasibility Agent returns
> `not_feasible`, the pipeline stops right here — it doesn't run Scope, Tech,
> or Timeline at all. I'll explain why that's there, and what happened
> before I added it, in the engineering highlights section.
>
> And the whole thing is wrapped in a broad exception handler, because this
> runs as an unsupervised background task — there's no caller waiting to
> catch an error it doesn't handle itself."

---

## ✅ TASK 5: Validation — LIVE DEMO
**Time target:** 6-8 minutes

This is the section where you actually run the app in front of your mentor.

### Demo #1 — a solid idea (prove the pipeline works end-to-end)

**🖥️ What to show:** browser tab `localhost:8000`, then the server terminal,
then `localhost:8000/docs`

**✅ Exact steps:**
1. On `localhost:8000`, register (or log in if already registered from the
   rehearsal) and go to the skill assessment page. Add exactly:
   - `Python` → `Advanced`
   - `Flask` → `Intermediate`
2. Go to submit idea. Enter:
   - **Title:** `Personal Library Book Recommender`
   - **Description:** `A web app where users log books they've read and get recommendations based on collaborative filtering.`
3. Submit. **Say out loud:** "Notice the response came back instantly with
   `status: submitted` — that's the Milestone 1 background-task hook firing;
   the request isn't blocked waiting for four LLM calls."
4. Switch to the server terminal. As the print lines appear one by one
   (`[feasibility]`, `[scope]`, `[tech]`, `[timeline]`, each ~20-30 seconds
   total), narrate: "You can see each agent completing in sequence, with its
   token usage." While waiting, you can glance back at the pipeline
   architecture slide instead of standing in silence.
5. Refresh the ideas list on `localhost:8000` — the status pill now reads
   `analyzed`.
6. Switch to `localhost:8000/docs`. Find `GET /api/ideas/{idea_id}/blueprint`
   under the `ideas` section. Click **Try it out**. Paste the idea's ID
   (visible in the ideas list page, or in the terminal logs). Click
   **Execute**.
7. Scroll the JSON response. **Point specifically at:**
   - `feasibility.verdict` and `feasibility.reasoning`
   - `scope.objectives` / `scope.deliverables` / `scope.out_of_scope`
   - `tech.stack[].reasoning` — **this is the skill-weighting proof**, say:
     "Notice it recommended Flask, and the reasoning explicitly references
     the intermediate Flask skill I just entered."
   - `timeline.weeks` — count the weeks out loud, point out the last week is
     testing/polish, not new features.

### Demo #2 — a vague idea (prove it's not a rubber stamp)

**✅ Exact steps:**
1. Submit a second idea:
   - **Title:** `AI App`
   - **Description:** `An app that uses AI to help people.`
2. Switch to the terminal — **point out only `[feasibility]` prints this
   time**, nothing else runs.
3. Refresh the ideas list — status pill reads `analyzed` (not `failed` —
   the pipeline completed correctly, it just stopped early on purpose).
4. Pull up its blueprint in `/docs` the same way as step 6 above. Point out:
   `feasibility.verdict` is `not_feasible`, and `scope`, `tech`, `timeline`
   are all `null`.

**🗣️ What to say (covers both demos):**
> "For **Task 5**, I validated the full pipeline end-to-end against the real
> Gemini API — not mocked. You just watched two of the four scenarios I
> tested live: a solid, well-scoped idea that came back feasible with a
> skill-matched tech stack, and a vague idea that correctly came back not
> feasible and stopped cleanly, with nothing invented downstream.
>
> The other two scenarios I ran during validation were an overambitious
> idea — a full self-driving perception stack from scratch — which also
> correctly came back not feasible, with the agent suggesting a realistic
> scaled-down alternative using public datasets instead; and a dedicated
> skill-weighting check, which is the React/Node.js-versus-Django scenario I
> described in Task 3.
>
> This validation pass is also where I found and fixed two real bugs, which
> I want to walk through now, because I think they're the most interesting
> part of this milestone."

---

## 🗄️ Data Model & Structured Output
**Time target:** 2 minutes

**🖥️ What to show:** editor tabs `app/models.py` and `app/routers/ideas.py`

**✅ Steps:**
1. In `app/models.py`, scroll to lines 79, 96, 110, 123 — the four class
   definitions: `FeasibilityReport`, `ScopeDefinition`, `TechRecommendation`,
   `TimelinePlan`. Point out each has an `idea_id` foreign key.
2. In `app/routers/ideas.py`, scroll to line 86-87
   (`@router.get("/{idea_id}/blueprint")` / `def get_blueprint(...)`) — the
   endpoint you just used live in Demo #1 and #2.

**🗣️ What to say:**
> "Each agent writes to its own table, foreign-keyed to the project idea —
> that's an audit trail, not a single overwritten blob. Every response is
> constrained by a JSON schema generated straight from a Pydantic model, so
> the data is validated before it ever reaches the database. And this
> blueprint endpoint — which you just saw return that full JSON — joins all
> four tables and returns the latest result of each stage in one call."

---

## 🔧 Key Engineering Highlight: Bugs Found During Validation
**Time target:** 3 minutes

**🖥️ What to show:** editor tab `app/agents/pipeline.py`, scrolled to line 45
(the `not_feasible` gate) and line 116 (the broad `except`)

**✅ Steps:**
1. Point at line 45 again — this is the fix for bug #1.
2. Scroll to `app/agents/scope.py` / `tech.py` briefly and point at
   `max_output_tokens` (lines 40 and 49) — this is the fix for bug #2.

**🗣️ What to say:**
> "Two things broke during real testing, and both taught me something about
> building on an LLM API.
>
> **First — a hallucination bug.** Before I added this gate, when I
> submitted the vague idea, the Feasibility Agent correctly said 'not
> feasible' — but the Scope Agent, given almost nothing to work with,
> invented an entirely different, much more specific project: a
> syllabus-parsing NLP tool that the student never actually proposed. It had
> latched onto an example mentioned in the feasibility reasoning. I fixed
> this by gating the pipeline right here — a `not_feasible` verdict now
> stops everything after the Feasibility stage. There's nothing to scope for
> a rejected idea, so nothing downstream should pretend otherwise.
>
> **Second — a token budget bug.** Gemini's flash models do internal
> 'thinking' before producing visible output, and that thinking shares the
> same token budget as the actual response. On one run, thinking consumed
> most of the budget, and the JSON output got cut off mid-string — a real
> crash, caught by my error handling, but still a crash. I fixed it by
> raising `max_output_tokens` with enough headroom for both.
>
> I'm showing these because I think finding and fixing real bugs during
> validation is the actual point of Task 5 — not just running the happy path
> once and calling it done."

---

## 📊 Results & Next Steps
**Time target:** 2 minutes

**🖥️ What to show:** `Milestone2_Presentation.pptx`, slides 9-10

**✅ Steps:** Switch back to presentation mode, advance through the last two
slides while talking.

**🗣️ What to say:**
> "To summarize: all four validation scenarios now produce correct verdicts,
> coherent chained output between agents, and correct status transitions —
> and the model I used, `gemini-3.5-flash`, is on Gemini's free tier, so
> this entire validation pass required no billing.
>
> For Milestone 3, I'm planning to add the Risk Assessment Agent,
> conversational mentor interaction for ongoing check-ins, and progress
> tracking that adjusts the plan as the student updates their status."

---

## ⚠️ If something goes wrong live

- **Gemini call fails or is slow (rate limit, network hiccup):** don't
  troubleshoot on stage. Say "let's look at a run from earlier" and pull up
  the rehearsal idea's blueprint in `/docs` instead — it's already sitting
  in the database from §0.
- **Forgot to export `GEMINI_API_KEY` before starting the server:** the app
  still boots fine (that's the lazy-init fix). The idea will land on
  `status: failed` instead. This is actually fine to show and explain — it's
  the exact failure-handling behavior from the orchestration section — then
  restart the server with the key set and resubmit.
- **Mentor asks to see the frontend show the blueprint directly:** say
  plainly that a results page wasn't part of this milestone's scope (Task 5
  was validation, not a UI task), and `/docs` is standing in for it right
  now.

---

## 🙋‍♂️ Expected Q&A Preparation

* **Q: Why Gemini instead of the originally planned Anthropic API?**
  * *Answer:* "Gemini's `gemini-3.5-flash` model has a genuine free tier, so
    I could validate the pipeline against the real API — including finding
    the two bugs I just described — without needing a paid account. The
    architecture doesn't depend on the provider: swapping back to Claude or
    another model would only mean rewriting `app/agents/client.py` and the
    four agent files, not the pipeline logic, the database schema, or the
    API surface."
* **Q: How do you guarantee the LLM returns valid, usable data instead of
  free text you'd have to parse?**
  * *Answer:* "Every agent call passes a JSON schema generated directly from
    a Pydantic model via `response_json_schema`. The response is validated
    against that schema before it's ever written to the database — so a
    malformed or incomplete response fails loudly instead of silently
    corrupting the data."
* **Q: What happens if the Gemini API call fails partway through the
  pipeline?**
  * *Answer:* "The whole pipeline runs inside one try/except in
    `run_pipeline`. Any failure — API error, missing key, malformed response
    — rolls back the database transaction and sets `idea.status = 'failed'`.
    Since this runs as an unsupervised FastAPI background task, there's no
    caller to catch an exception it doesn't handle itself, so the exception
    handling is deliberately broad rather than narrowly scoped to one error
    type."
* **Q: Why does the pipeline stop after a 'not_feasible' verdict instead of
  still generating a scope and timeline?**
  * *Answer:* "Because I tested it and watched it fail — the Scope Agent
    invented a project the student never proposed rather than admit there
    was nothing to scope. Stopping the pipeline there isn't a workaround,
    it's the correct behavior: a real mentor wouldn't hand a student a
    week-by-week plan for an idea they just rejected."
* **Q: Why doesn't the frontend show the blueprint results directly?**
  * *Answer:* "This milestone's scope was the agent pipeline and its
    validation, not a results UI — Task 5 in the brief is validation, not a
    frontend task. `/docs` gives full visibility into the exact same data a
    results page would show; building that page is a natural next step but
    wasn't required for this milestone."
