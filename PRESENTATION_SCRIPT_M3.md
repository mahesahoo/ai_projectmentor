# Milestone 3: Full Presentation Runbook (Say + Show + Do)

One document to follow start to finish — for every section: what to say
(verbatim), what to have on screen, and the exact clicks/commands to get
there. Pairs with `Milestone3_Presentation.pptx` for the slide visuals.

**Good news up front:** Milestone 2's presentation had one honest gap — the
frontend only showed a status pill, and you had to use `/docs` (Swagger UI)
to see actual agent output. That gap is closed. Every Milestone 3 feature —
risk assessment, chat, progress tracking, replanning, document generation —
is live in the main website itself, inside the "View analysis →" modal on
the ideas page. This demo runs entirely in the browser, no Swagger needed.

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
`[scope]`, `[tech]`, `[timeline]`, `[risk]`, `[mentor]`, `[replan]`,
`[docs:...]` print lines (with token counts) are your visible, live proof
each agent is actually executing, not a canned response.

**Then:**

1. **Do one full rehearsal run now**, before the mentor arrives: register a
   student, add 2 skill assessments, submit one idea, watch it reach
   `analyzed`, then run through chat, one progress log + replan, and
   generate one document (see §5 for the exact idea text and skills to
   use — use the same ones so this rehearsal doubles as your fallback data).
   This confirms the key works and you know the exact clicks.
2. **Wait a minute or two after the rehearsal** before presenting for real —
   Gemini's free tier has a requests-per-minute limit, and this milestone's
   demo alone makes ~8 separate agent calls (5 pipeline stages + chat +
   replan's 2 calls + a document) — don't stack that immediately behind a
   full rehearsal.
3. Open two browser tabs, both on `http://localhost:8000` (you won't need
   `/docs` for this milestone, but keep it bookmarked as a fallback — see
   §6).
4. Open these files as editor tabs, in this exact order (this is the order
   you'll walk through them):
   `app/agents/risk.py` → `app/agents/mentor.py` → `app/agents/replan.py` →
   `app/agents/docs.py` → `app/agents/pipeline.py` → `app/models.py` →
   `app/routers/ideas.py` → `frontend/index.html`.
5. Open `Milestone3_Presentation.pptx`, ready in presentation mode on slide 1.

---

## 🎙️ Introduction: Welcome & Overview
**Time target:** 1 minute

**🖥️ What to show:** `Milestone3_Presentation.pptx`, slide 1 (title slide).
Present in fullscreen/presentation mode. Don't switch windows during this part.

**✅ Steps:** Just talk over the title slide — no clicking needed yet.

**🗣️ What to say:**
> "Good morning/afternoon, Sir/Ma'am. Today, I am presenting the completion
> of **Milestone 3** of my academic project: the **AI Academic Project
> Mentor** platform.
>
> Quick recap — Milestone 1 built the foundation: onboarding, skills, idea
> submission. Milestone 2 built the multi-agent pipeline that turns a rough
> idea into a full blueprint: feasibility, scope, tech stack, and timeline.
>
> Milestone 3 is where the platform stops being a one-shot analyzer and
> becomes an ongoing mentor. Four things: a Risk Assessment Agent that
> completes the blueprint, a conversational mentor you can actually chat
> with, progress tracking that adapts the plan as the student falls behind
> or gets ahead, and on-demand documentation generation. Let's go through
> them one by one."

Advance to slides 2 and 3 (Objectives, Deliverables) and talk through their
bullet points directly off the slide — you already wrote those bullets
yourself, so no separate script is needed here; just read the slide content
naturally rather than word-for-word.

---

## ⚠️ TASK 1: Risk Assessment & Mitigation Agent
**Time target:** 2 minutes

**🖥️ What to show:** editor tab `app/agents/risk.py`

**✅ Steps:**
1. Scroll to line 8 (`SYSTEM_PROMPT = """...`). Point at lines 13-19 — the
   instruction that each risk needs a `risk`/`likelihood`/`mitigation`
   triple, and specifically the line telling it to be concrete ("Real-time
   notifications... eat the week 3 buffer") instead of generic ("scope
   creep").
2. Scroll to line 27 (`def run_risk_agent(...)`). Point at the function
   signature — it takes `objectives`, `deliverables`, `stack`, and `weeks`
   as input, i.e. the entire blueprint built so far. This is the pipeline's
   5th and final stage.

**🗣️ What to say:**
> "For **Task 1**, I extended the Milestone 2 pipeline with a fifth stage:
> the Risk Assessment Agent. It runs last, after Timeline, because it needs
> the complete picture — scope, tech stack, and the week-by-week plan — to
> say anything useful.
>
> The system prompt specifically instructs it to name a real risk tied to
> the actual plan, not generic advice. I'll show this live in a few
> minutes — every risk you'll see references a specific week or a specific
> technology choice, not boilerplate."

---

## 💬 TASK 2: Conversational Mentor
**Time target:** 2-3 minutes

**🖥️ What to show:** editor tab `app/agents/mentor.py`

**✅ Steps:**
1. Scroll to line 8 (`SYSTEM_PROMPT_TEMPLATE`). Point at the instruction to
   ground every answer in the actual blueprint and never invent a different
   project.
2. Scroll to line 76 (`def run_mentor_agent(...)`). Point at the `history`
   parameter and, below it, the loop building `types.Content(role=...)`
   objects — explain this is Gemini's native multi-turn chat format, not a
   single string with the whole conversation pasted in.
3. Switch to `app/routers/ideas.py`, scroll to line 154
   (`def send_chat_message(...)`). Point at line 169
   (`if idea.status != "analyzed":`) — the gate.

**🗣️ What to say:**
> "For **Task 2**, the Conversational Mentor is a real chat, not a form.
> Every message is grounded in the finished blueprint — the system prompt
> explicitly tells it not to invent requirements or suggest a different
> project.
>
> Technically, the interesting part is how conversation memory works. I'm
> using Gemini's native multi-turn `Content`/`Part` format — each prior
> message becomes its own typed turn with a role, `student` maps to `user`
> and `mentor` maps to `model`. That's different from just concatenating
> the whole conversation into one string, and it's what makes the model
> actually remember what was said two messages ago, which I'll prove live.
>
> One design choice to flag: unlike the blueprint pipeline, which runs as a
> background task with status polling, chat is synchronous — you send a
> message, you get a reply in the same request. That's the right shape for
> a chat; nobody wants to poll for a chat reply. And it's gated — you can't
> chat about an idea until its blueprint analysis is actually done, which
> makes sense, since there'd be nothing to ground the conversation in."

---

## 📈 TASK 3: Progress Tracking & Replan
**Time target:** 3 minutes

**🖥️ What to show:** editor tabs `app/models.py`, then `app/agents/replan.py`

**✅ Steps:**
1. In `app/models.py`, scroll to line 192 (`class ProgressUpdate(Base):`).
   Point at the docstring — logging is a "cheap, LLM-free log entry."
2. Switch to `app/agents/replan.py`, scroll to line 8 (`SYSTEM_PROMPT`).
   Point at the four numbered rules — especially "Return the FULL plan... not
   just the weeks that changed."
3. Switch to `app/routers/ideas.py`, scroll to line 245
   (`def replan_idea(...)`). Point at lines 266-271 — the guard that refuses
   to replan an idea with no scope/timeline (i.e. a rejected idea). Point at
   lines 281 and 288 — `db.add(TimelinePlan(...))` / `db.add(RiskAssessment(...))`
   — new rows, not updates to the old ones.

**🗣️ What to say:**
> "For **Task 3**, I split this into two deliberately separate actions.
> Logging progress — 'week 2, I'm behind on auth' — is just a database
> write, free, no LLM call, so a student can log as often as they want.
>
> Replanning is a separate, explicit action, because it costs two real agent
> calls: Timeline and Risk both rerun, using the full progress history as
> context. The Replan Agent doesn't patch the plan — it returns the entire
> revised timeline, marking finished weeks done and pushing back what's
> behind, extending the total duration only modestly if the delay actually
> warrants it.
>
> One thing I want to flag honestly: the brief describes this as progress
> updates 'triggering plan adjustments via the agent pipeline' — which reads
> like it should be automatic. I built it as an explicit action instead,
> specifically so a student logging progress five times a day doesn't
> silently trigger five expensive agent reruns. I'll explain my reasoning
> further if asked, but I want to be upfront that this is a deliberate,
> documented deviation, not an oversight.
>
> And notice — replanning doesn't overwrite the old timeline, it adds a new
> row. The old plan stays in the database as a history, same as every other
> agent output in this app."

---

## 📄 TASK 4: Documentation Generation
**Time target:** 2 minutes

**🖥️ What to show:** editor tab `app/agents/docs.py`

**✅ Steps:**
1. Scroll to line 8 (`BASE_TEMPLATE`). Point at the shared blueprint-context
   block that every document type reuses.
2. Scroll to line 43 (`DOC_INSTRUCTIONS`). Point at the three entries —
   `synopsis`, `methodology`, `progress_report` — and specifically the
   `progress_report` instructions: "If no progress has been logged yet, say
   so explicitly... instead of fabricating completed work."

**🗣️ What to say:**
> "For **Task 4**, students can generate three documents on demand: a
> synopsis for approval, a technical methodology, and a progress report.
> All three share one blueprint-context template, and only differ in the
> specific instructions for that document type.
>
> The one I'm proudest of is the progress report's honesty constraint. It's
> explicitly instructed to say 'no progress has been logged yet' rather than
> inventing a status update — I tested this specifically, generating a
> progress report before logging anything, and it correctly said so instead
> of hallucinating completed work. I'll show both versions live — before and
> after logging progress."

---

## ⚙️ Orchestration: the Pipeline's 5th Stage
**Time target:** 1-2 minutes

**🖥️ What to show:** editor tab `app/agents/pipeline.py`

**✅ Steps:**
1. Scroll to line 115 (`idea.status = status.ANALYZING_RISK`). Point out
   this is the only structural change to the Milestone 2 orchestrator — one
   more stage appended after Timeline, same pattern as the other four.
2. Switch to `app/agents/status.py` briefly, point at line 9
   (`ANALYZING_RISK = "analyzing_risk"`) — the new status value slotted in
   between `analyzing_timeline` and `analyzed`.

**🗣️ What to say:**
> "The orchestration change here is intentionally small — Risk is just a
> fifth stage appended to the same chain, using the same persist-then-
> advance-status pattern as the other four. `idea.status` now moves through
> `analyzing_feasibility` all the way to `analyzing_risk` before landing on
> `analyzed`. I kept it structurally identical to Milestone 2 on purpose —
> no reason to redesign something that already worked."

---

## ✅ LIVE DEMO — all four features, one continuous walkthrough
**Time target:** 10-12 minutes

This is the section where you actually run the app in front of your mentor,
entirely in the browser — no Swagger this time.

### Step 1 — submit an idea and watch the full 5-agent pipeline

**🖥️ What to show:** browser tab `localhost:8000`, then the server terminal

**✅ Exact steps:**
1. Register (or log in if already registered from the rehearsal) and go to
   the skill assessment page. Add exactly:
   - `JavaScript` → `Intermediate`
   - `SQL` → `Beginner`
2. Go to submit idea. Enter:
   - **Title:** `Campus Lost & Found Tracker`
   - **Description:** `A web app where students can post items they lost or found on campus, search by category/location, and get notified on matches. Includes a simple admin view for the campus office to mark items as claimed.`
3. Submit. Switch to the server terminal. As the print lines appear
   (`[feasibility]`, `[scope]`, `[tech]`, `[timeline]`, `[risk]` — the whole
   chain finishes in well under a minute, ~40-45 seconds measured in
   rehearsal), narrate: "Five agents now, not four — you can see `risk`
   running last, after timeline."
4. Back on `localhost:8000`, the idea's status pill updates live (it polls
   automatically) until it reads `analyzed`.

### Step 2 — open the blueprint modal, show the Risk section

**✅ Exact steps:**
1. Click **View analysis →** on the idea.
2. Scroll through Feasibility → Scope → Tech Stack → Timeline (all
   Milestone 2, familiar) down to **Risks & Mitigations** — the new section.
3. **Point at:** the colored likelihood badges (green/amber/red for
   low/medium/high) and read one risk + its mitigation out loud. **Say:**
   "Notice this references an actual week from the timeline above, not a
   generic warning."

### Step 3 — chat with the mentor

**✅ Exact steps:**
1. Scroll down to **Ask your mentor**. Type: `What's the riskiest part of
   this project?` and hit Enter.
2. While the reply streams in, **say:** "This is a live call to Gemini,
   synchronous — no polling."
3. Read the reply — it should reference the actual Risk section content
   above. **Point this out explicitly:** "It's not just chatting generically
   — it's pulling from the exact risk assessment we just looked at."
4. Ask a follow-up: `Can you remind me what I just asked you?` — **say:**
   "This proves real conversation memory, not just a stateless single-turn
   call."

### Step 4 — log progress and trigger a replan

**✅ Exact steps:**
1. Scroll to **Progress & Replanning**. Log two entries:
   - Week `1`, text: `Backend scaffold done, but auth took 3 extra days.`
   - Week `2`, text: `Ticket CRUD API mostly done, blocked on file-upload for photo attachments.`
2. Click **Request replan →**. **Say while it runs:** "This is two agent
   calls — Timeline, then Risk — both using the progress I just logged as
   context."
3. When it finishes, scroll back up to **Timeline** — **point out:** early
   weeks are now marked completed, later weeks shifted to account for the
   delay. Scroll to **Risks & Mitigations** — point out at least one risk
   that's new or changed, tied to what was just logged (e.g. the file-upload
   blocker).

### Step 5 — generate documents

**✅ Exact steps:**
1. Scroll to **Documents**. Select **Progress Report** from the dropdown,
   click **Generate**.
2. Click the generated entry to expand it. **Point at:** it reflects the
   two progress entries just logged (the auth delay, the file-upload
   blocker) — not generic filler.
3. Generate **Synopsis** and **Methodology** too, briefly expand each.
   **Say:** "Synopsis reads like prose for an approval document; methodology
   is technical, headers and architecture; progress report is a status
   update grounded in what I just logged. Three different documents, same
   underlying blueprint."

**🗣️ What to say (covers the whole demo):**
> "What you just watched is one continuous student lifecycle, entirely in
> the website: submit an idea, get a full 5-agent blueprint including risk,
> chat with the mentor about it, report progress, trigger a replan that
> actually revises the plan, and generate documentation reflecting all of
> it. Milestone 2's demo needed Swagger to show any of this — this milestone
> closes that gap. Everything you saw is live in the main site."

---

## 🗄️ Data Model
**Time target:** 1-2 minutes

**🖥️ What to show:** editor tab `app/models.py`

**✅ Steps:**
1. Scroll to line 157 (`class RiskAssessment(Base):`), 173
   (`class MentorMessage(Base):`), 192 (`class ProgressUpdate(Base):`), 211
   (`class GeneratedDocument(Base):`) — four new tables, all foreign-keyed
   to `project_ideas`, same pattern as Milestone 2's four.

**🗣️ What to say:**
> "Four new tables, same audit-trail pattern as Milestone 2 — every agent
> output, every chat message, every progress log, every generated document
> gets its own row with a timestamp. Nothing gets silently overwritten
> anywhere in this app."

---

## 🔧 Key Engineering Highlight: Design Decisions & Edge Cases
**Time target:** 3 minutes

**🖥️ What to show:** `app/routers/ideas.py`, scrolled to the `replan_idea`
guard (lines 257-271)

**✅ Steps:**
1. Point at line 257 (`if idea.status != "analyzed":`) and line 266
   (`if not (scope and tech and timeline):`) — two separate guards, one for
   "pipeline not done yet," one for "nothing to replan."

**🗣️ What to say:**
> "I want to walk through one design decision and one thing I specifically
> tested for, because I think both say more about the engineering than the
> happy-path demo does.
>
> **The design decision** — I already mentioned this: the brief implies
> progress updates should automatically trigger replanning. I made it
> explicit instead. My reasoning: a student who logs progress multiple
> times a session shouldn't silently burn API calls each time. This is a
> documented tradeoff, not a missed requirement — it's written down in my
> build checklist along with the reasoning.
>
> **The edge case** — what happens if a student tries to chat, generate
> documents, or replan on an idea that came back `not_feasible`? There's no
> scope, tech stack, or timeline for those ideas — the Milestone 2 pipeline
> correctly stops early. I specifically tested this: chat and document
> generation both degrade gracefully, falling back to just the feasibility
> reasoning as context, no crash. Replan, on the other hand, correctly
> refuses with an error — there's genuinely nothing to replan. That's not
> an accident; both behaviors are exactly what should happen, and I verified
> both against the real API before calling this done."

---

## 📊 Results & Next Steps
**Time target:** 2 minutes

**🖥️ What to show:** `Milestone3_Presentation.pptx`, slides 9-10

**✅ Steps:** Switch back to presentation mode, advance through the last two
slides while talking.

**🗣️ What to say:**
> "To summarize: I ran a full continuous validation — one idea through all
> five pipeline agents, a two-turn chat with confirmed memory, two progress
> logs followed by a replan, and all three document types — plus a separate
> edge-case run on a deliberately vague idea to confirm graceful
> degradation. 37 of 38 automated checks passed against the real API; the
> one failure was a typo in my own test script, not an app bug.
>
> And like Milestone 2, this required no billing — `gemini-3.5-flash` stayed
> on the free tier the whole way through.
>
> For Milestone 4, the brief calls for a faculty monitoring dashboard —
> project health indicators and auto-generated summaries across all
> students — plus end-to-end testing and final documentation. That's the
> next milestone."

---

## ⚠️ If something goes wrong live

- **Gemini call fails or is slow (rate limit, network hiccup):** don't
  troubleshoot on stage. Say "let's look at a run from earlier" and reopen
  the rehearsal idea's blueprint modal instead — it's already sitting in
  the database from §0, chat/progress/documents included.
- **Forgot to export `GEMINI_API_KEY` before starting the server, or Gemini
  itself hiccups (e.g. a transient `503`):** the app still boots fine. The
  idea will land on `status: failed` for new submissions, and chat/replan/
  document requests return a clean `503` with a friendly message ("The AI
  mentor is temporarily unavailable...") instead of hanging or throwing a
  bare `500`. This is fine to show and explain — it's the same lazy-init
  and error-handling design from Milestone 2, now extended to the
  synchronous M3 endpoints too — then restart the server with the key set
  (or just retry, if it was transient).
- **Replan or chat returns a 409 unexpectedly:** check the idea's status
  pill first — both are gated on `analyzed`. If it's still
  `analyzing_something`, the pipeline just hasn't finished yet; wait for it.
- **A generated document looks short or repetitive:** this is a live LLM
  call, output quality has some run-to-run variance — if it looks off,
  it's fine to just regenerate live and say so ("let's try that again,
  since it's a live model call").
- **Mentor asks why replan doesn't happen automatically:** this is expected
  — see the Engineering Highlight section above and the Q&A entry below.
  Answer directly, don't get defensive; it's a documented, reasoned
  decision, not an oversight.

---

## 🙋‍♂️ Expected Q&A Preparation

* **Q: Why doesn't logging progress automatically trigger a replan, like the
  brief describes?**
  * *Answer:* "To keep API cost predictable. A student might log progress
    several times in one sitting — auto-replanning on every log entry would
    mean multiple Timeline and Risk agent calls the student didn't
    explicitly ask for. Making replan an explicit action means the student
    controls when the expensive step happens, while logging stays free and
    frequent. This is a documented tradeoff in my Milestone 3 checklist, not
    a missed requirement."
* **Q: How does the mentor actually remember earlier messages in the
  conversation?**
  * *Answer:* "Gemini's SDK supports native multi-turn conversations via
    typed `Content` objects, each with a role — `user` or `model` — and I
    map the stored `student`/`mentor` message roles onto that directly. Each
    prior message becomes its own turn in the request, not a single
    flattened string, so the model gets genuine conversation structure, the
    same way it would in Gemini's own chat interface."
* **Q: What happens if a student tries to chat or generate documents on a
  rejected (not_feasible) idea?**
  * *Answer:* "Both degrade gracefully — the mentor and document agents fall
    back to just the feasibility verdict and reasoning as context, since
    there's no scope, tech stack, or timeline to reference. I tested this
    specifically against the real API rather than assuming it. Replan is
    different — it correctly refuses with an error, since there's genuinely
    nothing to replan for a rejected idea."
* **Q: Why is chat synchronous but the original pipeline is a background
  task?**
  * *Answer:* "They have different UX expectations. Idea submission returns
    instantly and the pipeline runs in the background because nobody wants
    to sit on a loading screen for four sequential LLM calls before seeing
    their idea was received. A chat message, on the other hand, is expected
    to get an immediate reply — that's just how chat works — so it's a
    normal synchronous request. Different interaction, different pattern,
    used deliberately."
* **Q: How do you know the replan actually improved the plan, rather than
  just generating something different?**
  * *Answer:* "The Replan Agent's system prompt has explicit rules: mark
    completed weeks as done rather than repeating them, reschedule
    incomplete work realistically rather than pretending delays didn't
    happen, and only extend the total timeline modestly if genuinely
    needed. In my validation run, I logged a real blocker and watched the
    revised plan correctly push that work to a later week, and the Risk
    Agent — rerun with the same progress context — independently surfaced a
    new risk tied to exactly what I'd logged. That's not scripted; that's
    the model reasoning over the context it was given."
* **Q: Why persist a new row every time instead of updating the existing
  one — for the timeline, the risk assessment, the documents?**
  * *Answer:* "Audit trail. If a replan makes the plan worse, or a
    regenerated document is worse than the last one, overwriting would lose
    that history permanently. Every agent output in this app — going back
    to Milestone 2 — is append-only for that reason; `GET /blueprint` and
    `GET /documents` always surface the latest, but nothing is ever deleted
    automatically."
