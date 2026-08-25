# Milestone 4: Full Presentation Runbook (Say + Show + Do)

One document to follow start to finish — for every section: what to say
(verbatim), what to have on screen, and the exact clicks/commands to get
there. Pairs with `Milestone4_Presentation.pptx` for the slide visuals.

**This is the final milestone.** The brief specifies no Milestone 5 — by the
end of this presentation, the system is feature-complete: a full agent
pipeline, a conversational mentor, progress-driven replanning, on-demand
documentation, a faculty dashboard, an automated test suite, and honest
documentation of every design decision and known limitation. This script
covers all four Milestone 4 tasks and closes with the whole project's arc.

---

## 0. Pre-Presentation Setup — do this 10-15 minutes before the mentor arrives

**Exact commands, in order:**

```bash
cd /home/mahesh/mics
source venv/bin/activate
export GEMINI_API_KEY="..."          # your real key
echo $GEMINI_API_KEY                  # confirm it printed, not empty
rm -f project_mentor.db               # start from a clean database
uvicorn app.main:app --reload
```

⚠️ **Same warning as every milestone:** if a server from an earlier session
is already running, stop it first (`Ctrl+C`) *before* deleting
`project_mentor.db` — deleting the DB file out from under a live `--reload`
server corrupts its connection. If registration/login suddenly start
returning `500` while `/docs` still loads fine, that's the symptom; the fix
is `Ctrl+C` and rerun `uvicorn app.main:app --reload`.

Leave that terminal window running and visible — the `[feasibility]`,
`[scope]`, `[tech]`, `[timeline]`, `[risk]`, `[mentor]`, `[replan]`,
`[docs:...]`, and now `[faculty_summary]` print lines are your visible, live
proof each agent is actually executing.

**Then:**

1. **Do one full rehearsal run now**, before the mentor arrives: register a
   student, submit one idea, watch it reach `analyzed`, log one progress
   entry, flip a second account to faculty (§5 Step 1 has the exact command),
   and generate one faculty summary. This confirms the key works and you know
   the exact clicks.
2. **Also run the automated test suite once**, so you know it's green and
   fast before demoing it live:
   ```bash
   pytest
   ```
   Expect `25 passed, 1 deselected` in well under 10 seconds.
3. **Wait a minute or two after the rehearsal** before presenting for real —
   the free tier has a requests-per-minute limit, and between the pipeline (5
   calls) and one summary generation (1 call), the rehearsal alone makes
   several calls.
4. Open two browser tabs on `http://localhost:8000` — one you'll register a
   student in, one you'll flip to faculty and use for the dashboard.
5. Open a second terminal for the `pytest` demo — don't reuse the server's
   terminal, so the print-line output stays visible throughout.
6. Open these files as editor tabs, in this order: `app/agents/faculty_summary.py`
   → `app/routers/faculty.py` → `app/auth.py` → `tests/conftest.py` →
   `app/routers/ideas.py`.
7. Open `Milestone4_Presentation.pptx`, ready in presentation mode on slide 1.

---

## 🎙️ Introduction: Welcome & Overview
**Time target:** 1 minute

**🖥️ What to show:** `Milestone4_Presentation.pptx`, slide 1 (title slide).

**✅ Steps:** Talk over the title slide — no clicking needed yet.

**🗣️ What to say:**
> "Good morning/afternoon, Sir/Ma'am. Today is **Milestone 4** — the final
> milestone — of the **AI Academic Project Mentor** platform.
>
> Quick recap: Milestone 1 built onboarding and idea submission. Milestone 2
> built the 4-agent pipeline that turns a rough idea into a blueprint.
> Milestone 3 turned that one-shot analyzer into an ongoing mentor — risk
> assessment, chat, progress tracking with replanning, and document
> generation.
>
> Milestone 4 closes the loop with four things: a faculty dashboard giving a
> mentor a health-at-a-glance view across every student, an automated
> end-to-end test suite, a genuine reliability pass on the prompts and the
> pipeline, and final documentation. Let's go through them."

Advance to slides 2 and 3 (Objectives, Deliverables) and talk through their
bullet points directly off the slide.

---

## 📊 TASK 1: Faculty Monitoring Dashboard
**Time target:** 3 minutes

**🖥️ What to show:** editor tabs `app/agents/faculty_summary.py`, then
`app/routers/faculty.py`, then `app/auth.py`

**✅ Steps:**
1. In `faculty_summary.py`, scroll to line 8 (`SYSTEM_PROMPT`). Point at the
   instruction to synthesize, not restate — "your value is judgment... not a
   compressed re-listing of objectives or tasks the faculty member could
   read themselves one section up."
2. Scroll to line 37 (`def run_faculty_summary_agent(...)`). Point at the
   input signature — the full blueprint, progress notes, *and* two
   engagement signals (`replan_count`, `chat_message_count`) that no other
   agent in this app receives.
3. Switch to `app/routers/faculty.py`, scroll to line 24
   (`def _compute_health_indicators(...)`). Point at line 44
   (`weeks_completed = max(week_numbers, default=0)`) and explain this is
   deliberately *not* parsed from the timeline's task text.
4. Switch to `app/auth.py`, scroll to line 59 (`def get_current_faculty(...)`).
   Point at line 68 (`if not current_student.is_faculty:`) — the entire
   faculty-access mechanism is this one check.

**🗣️ What to say:**
> "For **Task 1**, the dashboard has two parts, and I built them very
> differently on purpose.
>
> The health *indicators* — weeks completed, high-risk count, replan count,
> days since last update, chat engagement — are computed directly from
> existing tables. Zero LLM calls. A `COUNT()` and a `max()` already answer
> those questions; there's no reason to spend API quota generating something
> deterministic.
>
> The one thing that *is* generated is a short natural-language summary plus
> a health tag — `on_track`, `at_risk`, `stalled`, or `not_feasible` — from a
> 9th agent. Its system prompt explicitly forbids restating the blueprint;
> the value is synthesis, naming the one thing a faculty member should
> actually know right now. And it's generated only when a faculty member
> explicitly asks — same on-demand discipline as replan and document
> generation from Milestone 3.
>
> One more thing on `weeks_completed`: I initially tried deriving it by
> looking for the word 'Completed:' inside the timeline's task text. That's
> wrong — that word only appears there after a replan, because it's prose
> the replan agent happens to write, not a structured field. I caught this
> before writing any code, while drafting the build checklist, and switched
> to reading it straight off the student's own logged progress instead.
>
> And access: there's no faculty registration flow. `is_faculty` is a plain
> boolean on the same `Student` table, checked by one dependency that wraps
> the same JWT auth every other route already uses. Building a whole second
> account type would be scope creep for what the brief actually asks for."

---

## 🧪 TASK 2: End-to-End Automated Testing
**Time target:** 3 minutes

**🖥️ What to show:** editor tab `tests/conftest.py`, then a terminal

**✅ Steps:**
1. Scroll to the top comment block in `conftest.py`. Point at the
   explanation of why `DATABASE_URL` is set *before* any `app.*` import,
   rather than using a `dependency_overrides[get_db]` patch alone.
2. Switch to `app/routers/ideas.py`, scroll to line 65
   (`def _call_agent(fn, *args, **kwargs):`) — point out this is also the
   seam the test suite patches to mock agent calls.
3. Switch to a terminal and actually run it live:
   ```bash
   pytest
   ```

**🗣️ What to say (while `pytest` runs — it finishes in seconds):**
> "For **Task 2**, this milestone added a real automated test suite — 26
> tests total. 25 of them mock every agent call and run in under 10 seconds,
> which you're watching right now. Exactly one test is marked `@pytest.mark.live`
> and actually calls the real Gemini API — that one's excluded by default,
> since it costs real quota, but it's what proves the mocks aren't hiding a
> real wiring problem.
>
> The tricky part was database isolation. This app's background pipeline
> builds its own database session directly, bypassing FastAPI's normal
> dependency injection — so a standard test-isolation pattern that only
> overrides the injected session would still let the pipeline write to the
> real database. I set the database URL before any part of the app gets
> imported instead, which is the one approach that actually covers both
> paths. I confirmed this by checking the real database's file timestamp
> before and after running the entire suite — untouched.
>
> I also had to be careful about *where* I patch each agent function. Three
> different files import the same agent — the pipeline, the ideas router,
> and the faculty router each hold their own reference, bound at import
> time. Patching the wrong one silently does nothing; the test would pass
> without actually testing anything. I mention this because it's exactly the
> kind of bug that looks fine until you check."

---

## 🔍 TASK 3: Prompt & Pipeline Reliability Pass
**Time target:** 3 minutes

**🖥️ What to show:** editor tab `app/agents/faculty_summary.py`, then
`app/agents/mentor.py`

**✅ Steps:**
1. In `faculty_summary.py`, scroll to line 83 (`max_output_tokens=1500,`).
   Point at the comment above it explaining the original value was 600.
2. Switch to `app/agents/mentor.py`, find the `max_output_tokens=2048` line
   and its comment — the tightest budget in the app, found the same way.

**🗣️ What to say:**
> "For **Task 3**, I did a genuine reliability audit, not a cosmetic one.
>
> The real find: `gemini-3.5-flash` spends part of its output token budget
> on internal reasoning — 'thinking' tokens — before it produces any visible
> text. I measured this directly: one real call burned about 570 tokens on
> thinking alone. The Faculty Summary agent's original budget of 600 left
> almost nothing for the actual JSON, and it silently truncated mid-string.
> I found this the moment I first tested the agent live, not through code
> review — fixed it, then went back and checked every other agent's budget
> against the same risk, and bumped the next-tightest one too.
>
> I also re-read all nine system prompts back to back and found one small
> naming inconsistency — one agent called itself a 'module' where the other
> eight all say 'Agent' — and confirmed the anti-generic-output instruction
> every agent has still actually holds up.
>
> The most interesting finding, though, is about retries — I'll walk through
> that as its own section, because it's a good story about verifying instead
> of assuming."

---

## ✅ LIVE DEMO — faculty dashboard, end to end
**Time target:** 6-8 minutes

**🖥️ What to show:** two browser tabs, `localhost:8000`

### Step 1 — set up a student and a faculty account

**✅ Exact steps:**
1. In tab A: register/log in as a student, submit an idea (reuse one from
   the rehearsal if it's already `analyzed` — saves ~40 seconds live). Log
   one progress entry.
2. In tab B: register/log in as a second account. In the server's terminal
   (a second one, or a quick `Ctrl+Z`/background if needed), flip it to
   faculty:
   ```bash
   python3 -c "
   from app.database import SessionLocal
   from app.models import Student
   db = SessionLocal()
   s = db.query(Student).filter(Student.email == 'YOUR_FACULTY_EMAIL').first()
   s.is_faculty = True
   db.commit()
   "
   ```
3. In tab B, log out and back in (or just refresh) — the **Faculty
   dashboard** nav item now appears in the sidebar. **Say:** "There's no
   faculty sign-up screen — this flip is the entire provisioning story, and
   that's a deliberate, documented choice, not a missing feature."

### Step 2 — the dashboard

**✅ Exact steps:**
1. Click **Faculty dashboard**. Point at the student's idea row — status
   pill, computed indicators (weeks, risk count, replan count, chat count),
   and "No summary yet."
2. Click **Generate summary** on that row. **Say while it runs:** "This is
   the one real Gemini call on this whole page — everything else you saw
   was already computed."
3. Point at the health badge that appears, and read the summary text aloud.
   **Say:** "Notice it's not restating the blueprint — it's telling me
   something I'd otherwise have to read the whole project to find out."

### Step 3 — the detail view

**✅ Exact steps:**
1. Click **View details →** on the same row.
2. Scroll through the read-only blueprint, then the progress log, then the
   mentor conversation, then the summary at the bottom.
3. **Say:** "This reuses the exact same rendering code as the student's own
   blueprint modal — I factored that out specifically so the two views can
   never drift apart from each other."

**🗣️ What to say (covers the whole demo):**
> "What you just watched is the faculty half of this platform: zero-cost
> aggregation across every student, and one deliberate, on-demand AI call
> per project when a faculty member actually wants a synthesis. Nothing here
> runs automatically or silently burns quota."

---

## 🗄️ Data Model
**Time target:** 1 minute

**🖥️ What to show:** editor tab `app/models.py`

**✅ Steps:**
1. Scroll to line 24 (`is_faculty = Column(Boolean, ...)`) inside `Student`.
2. Scroll to line 236 (`class ProjectSummary(Base):`) — the 12th and final
   table, same audit-trail pattern as every other agent-output table.

**🗣️ What to say:**
> "One new column, one new table. `is_faculty` on the existing `Student`
> row, and `ProjectSummary` — new row per generation, never overwritten,
> same rule as every agent output since Milestone 2."

---

## 🔧 Key Engineering Highlight: Verify, Don't Assume
**Time target:** 3 minutes

**🖥️ What to show:** editor tab `app/routers/ideas.py`, scrolled to line 65
(`def _call_agent`)

**✅ Steps:**
1. Point at line 83 — the `print(...)` line logging the underlying exception
   before converting it to a clean `503`.

**🗣️ What to say:**
> "I want to walk through one investigation, because it's the best example
> of this milestone's actual engineering.
>
> The question was: does the Gemini SDK automatically retry failed calls
> before giving up? I'd actually written down — incorrectly — in an earlier
> planning note that it did, based on a traceback I'd seen where a call
> failed and the error trace showed what looked like a retry sequence.
>
> I traced the SDK's own source directly instead of trusting that note. The
> actual answer: `genai.Client()`, constructed the way this app constructs
> it, retries *nothing* — one attempt, and it fails immediately if that
> attempt fails. What I'd seen in that earlier traceback was the retry
> library's wrapper code showing up in the stack trace even though zero
> retries actually happened — a single attempt still gets wrapped in the
> same machinery, so the trace looks similar either way.
>
> Once I had the real answer, I made a deliberate call not to add retry
> anyway. The most common real failure this project hits during heavy
> testing is the free tier's daily quota limit — and that specific error
> code is one the SDK would normally retry, except retrying it can't
> possibly succeed. Adding retry would just make a demo audience wait
> several extra seconds for the exact same failure. I'd rather fail fast
> with a clean message, which is what this `_call_agent` helper already
> does — and I added that one print line you're looking at during this
> exact investigation, because without it, I couldn't tell a real bug apart
> from a quota limit from the server log alone.
>
> I corrected the wrong note before it could reach the README or the
> project report. I think that's worth saying out loud: even something I
> wrote down earlier in this same project needed re-checking, not just
> trusting."

---

## 📊 Results & Next Steps
**Time target:** 2 minutes

**🖥️ What to show:** `Milestone4_Presentation.pptx`, last two slides

**✅ Steps:** Switch back to presentation mode, advance through the last two
slides while talking.

**🗣️ What to say:**
> "To summarize: 26 automated tests, all passing — 25 mocked and fast, one
> live against the real API. The full faculty flow was also validated live,
> against a real running server with real Gemini calls, not just the
> automated suite's mocks. Two real bugs were found and fixed during this
> milestone alone — a token-budget truncation, and a missing error-state
> guard in the faculty view's frontend rendering — both documented in the
> project report, not smoothed over.
>
> And like every milestone before it, this required no billing —
> `gemini-3.5-flash` stayed on Gemini's free tier the whole way through,
> even with all the live testing this milestone needed.
>
> This is the final milestone. The brief specifies no Milestone 5. The
> system covers idea submission, a 5-agent blueprint pipeline, a
> conversational mentor, progress tracking with replanning, on-demand
> documentation, and now a faculty dashboard — plus an automated test suite
> and a full project report documenting every design decision, every
> deviation from the brief's literal wording, and every known limitation,
> honestly."

---

## ⚠️ If something goes wrong live

- **Gemini call fails or is slow (rate limit, network hiccup):** don't
  troubleshoot on stage. Say "let's look at the rehearsal data" and reopen
  the faculty dashboard instead — the rehearsal's summary is already there.
- **`429` quota error during the demo:** this is expected behavior, not a
  bug — say so directly. "That's the free tier's daily limit, and you're
  watching the exact clean-failure behavior I built and tested for it" is a
  perfectly good thing to say live if it happens.
- **`pytest` shows a failure during the live test-suite demo:** don't debug
  on stage. Say "let me show you the last confirmed-green run" and have a
  terminal screenshot or the commit history ready as a fallback — but this
  should not happen if §0's rehearsal step was actually run beforehand.
- **Faculty dashboard is empty:** confirm the flipped account actually has
  `is_faculty = True` (a typo'd email in the flip command is the most likely
  cause) and that the student account has at least one submitted idea.
- **Mentor asks why there's no faculty sign-up page:** this is expected —
  see the Task 1 script and the Q&A entry below. Answer directly.

---

## 🙋‍♂️ Expected Q&A Preparation

* **Q: Why not build a real faculty registration/login system?**
  * *Answer:* "The brief asks for a monitoring dashboard, not a second
    account type with its own sign-up flow — building one would be real
    scope creep for a milestone budgeted around ten hours. A boolean flag
    plus one auth check gets the same security properties — the same JWT,
    the same expiry, the same hashing — for free, since it reuses
    infrastructure that already exists rather than duplicating it."
* **Q: Does the Gemini SDK retry failed requests automatically?**
  * *Answer:* "No — I traced the actual source rather than assuming. With
    no explicit retry configuration, which is how this app constructs its
    client, it makes exactly one attempt and fails immediately if that
    attempt fails. I considered adding retry and decided against it,
    because the most common real failure here — daily quota exhaustion —
    can't be fixed by retrying, so it would only add delay before an
    identical failure."
* **Q: How do your tests avoid hitting the real Gemini API and burning your
  quota every time you run them?**
  * *Answer:* "25 of the 26 tests patch the agent functions directly, so no
    network call happens at all — they test routing, persistence, and
    gating logic, not the model's actual output quality. Exactly one test
    is marked to run only when explicitly requested, and that's the one
    that proves the real wiring still works end to end."
* **Q: How do you know `weeks_completed` on the dashboard is actually
  correct?**
  * *Answer:* "It's read directly from the student's own logged progress —
    the highest week number they've reported — not inferred from anything
    the AI generates. I specifically avoided parsing it out of the
    timeline's task descriptions, because that text is free-form prose from
    an agent, not a structured field, and it only exists at all after a
    replan."
* **Q: What would Milestone 5 have been, if there was one?**
  * *Answer:* "There isn't one — this is the final milestone per the brief.
    If I were continuing past it, the honest next steps are in the project
    report's limitations section: a real faculty-provisioning flow instead
    of a manual database flip, bounding the chat context window for very
    long conversations, and production deployment concerns like process
    management and secrets handling that were out of scope for an academic
    milestone project."
