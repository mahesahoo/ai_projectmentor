from typing import List

from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import TechStackItem, TimelineAgentOutput, WeekPlan

SYSTEM_PROMPT = """You are the Timeline Planning Agent handling a REPLAN request in an AI \
Academic Project Mentor pipeline. The student already has a week-wise plan and has reported \
progress against it. Produce a REVISED full week-wise plan that accounts for that progress.

Rules:
- Weeks the student reports as done should be reflected as completed (short task list, or state \
  the deliverable was finished) - don't repeat finished work as upcoming tasks.
- Weeks reported as behind, blocked, or harder than expected should have their remaining tasks \
  rescheduled realistically into later weeks - don't pretend the delay didn't happen.
- Keep the same total week count as the original plan unless the reported progress clearly \
  requires more time, in which case extend it modestly (1-2 extra weeks, not double).
- Return the FULL plan (all weeks, "week" and "tasks"), not just the weeks that changed - the \
  frontend replaces the whole timeline with this response.
- Stay grounded in the original scope and tech stack; a replan adjusts pacing, it doesn't change \
  what's being built."""


def run_replan_agent(
    title: str,
    description: str,
    objectives: List[str],
    deliverables: List[str],
    stack: List[TechStackItem],
    original_weeks: List[WeekPlan],
    progress_notes: List[str],
) -> TimelineAgentOutput:
    stack_text = "\n".join(
        f"- {item.category}: {item.technology} ({item.reasoning})" for item in stack
    )
    original_weeks_text = "\n".join(
        f"Week {w.week}: " + "; ".join(w.tasks) for w in original_weeks
    )
    progress_text = "\n".join(f"- {n}" for n in progress_notes) or "(no progress logged yet)"
    user_content = (
        f"Project idea:\nTitle: {title}\nDescription: {description}\n\n"
        f"Scope objectives:\n" + "\n".join(f"- {o}" for o in objectives) + "\n\n"
        f"Scope deliverables:\n" + "\n".join(f"- {d}" for d in deliverables) + "\n\n"
        f"Recommended tech stack:\n{stack_text}\n\n"
        f"Original timeline:\n{original_weeks_text}\n\n"
        f"Student-reported progress (chronological):\n{progress_text}"
    )
    response = get_client().models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=TimelineAgentOutput.model_json_schema(),
            max_output_tokens=4000,
        ),
    )
    print(
        f"[replan] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return TimelineAgentOutput.model_validate_json(response.text)
