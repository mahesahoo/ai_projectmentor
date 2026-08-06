from typing import List, Optional

from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import RiskAgentOutput, TechStackItem, WeekPlan

SYSTEM_PROMPT = """You are the Risk Assessment and Mitigation Agent in an AI Academic Project \
Mentor pipeline. You receive a student's project idea, its scope, its recommended technology \
stack, and its week-wise timeline. Identify what is realistically likely to go wrong for a \
student (not a professional team) building this, and how to prevent or recover from it.

Return "risks": a list of entries, each with:
- "risk": a specific, concrete failure mode grounded in THIS project (e.g. "Real-time \
  notifications via WebSockets may be new territory and eat the week 3 buffer", not a generic \
  "scope creep" with no connection to the actual plan).
- "likelihood": "low", "medium", or "high".
- "mitigation": a concrete, actionable step the student can take now or when the risk starts \
  to materialize - not vague advice like "manage time well".

Cover a mix of technical risks (unfamiliar tech, integration complexity), scope/timeline risks \
(a week or deliverable that's clearly tight), and academic-project-specific risks (single point \
of failure since it's often one student, external API dependency, data availability). Return \
3-6 risks - enough to be useful, not a padded list of trivial ones."""


def run_risk_agent(
    title: str,
    description: str,
    objectives: List[str],
    deliverables: List[str],
    stack: List[TechStackItem],
    weeks: List[WeekPlan],
    progress_notes: Optional[List[str]] = None,
) -> RiskAgentOutput:
    stack_text = "\n".join(
        f"- {item.category}: {item.technology} ({item.reasoning})" for item in stack
    )
    weeks_text = "\n".join(
        f"Week {w.week}: " + "; ".join(w.tasks) for w in weeks
    )
    user_content = (
        f"Project idea:\nTitle: {title}\nDescription: {description}\n\n"
        f"Scope objectives:\n" + "\n".join(f"- {o}" for o in objectives) + "\n\n"
        f"Scope deliverables:\n" + "\n".join(f"- {d}" for d in deliverables) + "\n\n"
        f"Recommended tech stack:\n{stack_text}\n\n"
        f"Timeline:\n{weeks_text}"
    )
    if progress_notes:
        user_content += (
            "\n\nStudent-reported progress so far (this is a REPLAN - weigh these "
            "when judging what's now more or less risky):\n"
            + "\n".join(f"- {n}" for n in progress_notes)
        )
    response = get_client().models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=RiskAgentOutput.model_json_schema(),
            max_output_tokens=3000,
        ),
    )
    print(
        f"[risk] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return RiskAgentOutput.model_validate_json(response.text)
