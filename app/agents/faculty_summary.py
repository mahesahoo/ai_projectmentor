from typing import List

from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import ProjectSummaryAgentOutput, RiskItem, TechStackItem, WeekPlan

SYSTEM_PROMPT = """You are the Faculty Summary Agent in an AI Academic Project Mentor platform. \
A faculty member monitoring many students at once will read what you write - they have seconds, \
not minutes, per project. You are given one student's full project blueprint, their logged \
progress updates, and two engagement signals (how many times the plan has been replanned, how \
many mentor chat messages they've sent).

Return "summary": 2-4 sentences a faculty member can read in about 10 seconds. SYNTHESIZE, don't \
restate - the blueprint and progress log are given to you in full below; your value is judgment \
("on track but slipping on the Week 4 file-upload blocker" or "no progress logged in 3 weeks \
despite an ambitious plan"), not a compressed re-listing of objectives or tasks the faculty \
member could read themselves one section up. Name the single most important thing they should \
know right now, if there is one.

Return "health_status", one of:
- "not_feasible" - the feasibility verdict below is "not_feasible". Say briefly why, based on \
  the feasibility reasoning given - do not invent scope/timeline details that don't exist for a \
  project that was never scoped.
- "on_track" - progress logged is consistent with the timeline, no major blockers reported, or \
  too early to expect progress yet with nothing concerning so far.
- "at_risk" - some signal of trouble: a reported blocker, a stalled area, high-likelihood risks \
  clustering near the current point in the timeline, or a wide gap between plan and progress.
- "stalled" - little or no progress reported for a project that should be well underway, or \
  progress notes describe being stuck without forward movement across multiple entries.

Base "health_status" on the actual evidence below, not on the verdict/risk list alone - a \
"feasible" project with several high-likelihood risks but strong logged progress is "on_track", \
not "at_risk", because risks are anticipated problems, not ones that have happened."""


def run_faculty_summary_agent(
    title: str,
    description: str,
    verdict: str,
    feasibility_reasoning: str,
    objectives: List[str],
    deliverables: List[str],
    stack: List[TechStackItem],
    weeks: List[WeekPlan],
    risks: List[RiskItem],
    progress_notes: List[str],
    replan_count: int,
    chat_message_count: int,
) -> ProjectSummaryAgentOutput:
    user_content = (
        f"Project idea:\nTitle: {title}\nDescription: {description}\n\n"
        f"Feasibility: {verdict} - {feasibility_reasoning}\n\n"
        f"Scope objectives:\n" + ("\n".join(f"- {o}" for o in objectives) or "(none)") + "\n\n"
        f"Scope deliverables:\n" + ("\n".join(f"- {d}" for d in deliverables) or "(none)") + "\n\n"
        f"Recommended tech stack:\n"
        + ("\n".join(f"- {s.category}: {s.technology}" for s in stack) or "(none)")
        + "\n\n"
        f"Timeline:\n"
        + ("\n".join(f"Week {w.week}: " + "; ".join(w.tasks) for w in weeks) or "(none)")
        + "\n\n"
        f"Known risks:\n"
        + ("\n".join(f"- [{r.likelihood}] {r.risk}" for r in risks) or "(none)")
        + "\n\n"
        f"Progress logged so far:\n"
        + ("\n".join(f"- {n}" for n in progress_notes) or "(no progress logged yet)")
        + "\n\n"
        f"Engagement signals: {replan_count} replan(s) requested, {chat_message_count} mentor "
        f"chat message(s) sent."
    )
    response = get_client().models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=ProjectSummaryAgentOutput.model_json_schema(),
            # gemini-3.5-flash spends part of this budget on internal "thinking"
            # tokens before any visible output (observed ~570 thinking tokens on
            # a run with this prompt) - a low budget sized only for the short
            # visible summary truncates mid-JSON. Sized with real headroom, not
            # just "how long is the output I want".
            max_output_tokens=1500,
        ),
    )
    print(
        f"[faculty_summary] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return ProjectSummaryAgentOutput.model_validate_json(response.text)
