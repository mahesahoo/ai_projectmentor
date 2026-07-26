from typing import List

from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import TechStackItem, TimelineAgentOutput

SYSTEM_PROMPT = """You are the Timeline Planning Agent in an AI Academic Project Mentor \
pipeline. You receive a student's project idea, its defined scope, and the recommended \
technology stack. Produce a week-wise execution plan.

Return "weeks": a list of entries, each with a "week" number (starting at 1) and "tasks" - a \
short list of concrete, actionable tasks for that week (e.g. "Set up FastAPI project skeleton \
and database schema", not "backend work").

Default to a plan spanning 6-8 weeks unless the scope clearly implies otherwise. Sequence \
tasks so dependencies make sense (e.g. don't schedule frontend integration before the API it \
depends on exists). Leave the final week for testing, polish, and documentation rather than \
new feature work."""


def run_timeline_agent(
    title: str,
    description: str,
    objectives: List[str],
    deliverables: List[str],
    stack: List[TechStackItem],
) -> TimelineAgentOutput:
    stack_text = "\n".join(
        f"- {item.category}: {item.technology} ({item.reasoning})" for item in stack
    )
    user_content = (
        f"Project idea:\nTitle: {title}\nDescription: {description}\n\n"
        f"Scope objectives:\n" + "\n".join(f"- {o}" for o in objectives) + "\n\n"
        f"Scope deliverables:\n" + "\n".join(f"- {d}" for d in deliverables) + "\n\n"
        f"Recommended tech stack:\n{stack_text}"
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
        f"[timeline] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return TimelineAgentOutput.model_validate_json(response.text)
