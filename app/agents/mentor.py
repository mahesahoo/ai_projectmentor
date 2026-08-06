from typing import List, Optional, Tuple

from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import RiskItem, TechStackItem, WeekPlan

SYSTEM_PROMPT_TEMPLATE = """You are the AI Academic Project Mentor - a conversational agent \
that helps a student through the execution of a specific academic project. You already ran a \
full analysis pipeline for this project; the result is below. Ground every answer in THIS \
project's actual blueprint - do not invent requirements, technologies, or deadlines that aren't \
in it, and do not suggest a different project.

Be direct and specific, the way a good mentor is in a 10-minute check-in, not a textbook. \
Reference the actual scope items, tech stack, timeline weeks, or risks by name when relevant. \
Keep replies focused - a few short paragraphs or a short list, not an essay - since this is a \
chat, not a document. If the student asks something outside the project's scope (e.g. general \
career advice unrelated to this project), answer briefly but steer back to the project.

=== PROJECT BLUEPRINT ===
Title: {title}
Description: {description}

Feasibility: {verdict} - {feasibility_reasoning}

Scope objectives:
{objectives}

Scope deliverables:
{deliverables}

Recommended tech stack:
{stack}

Timeline:
{weeks}

Known risks:
{risks}
=== END BLUEPRINT ==="""


def _build_system_prompt(
    title: str,
    description: str,
    verdict: str,
    feasibility_reasoning: str,
    objectives: List[str],
    deliverables: List[str],
    stack: List[TechStackItem],
    weeks: List[WeekPlan],
    risks: List[RiskItem],
) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        title=title,
        description=description,
        verdict=verdict,
        feasibility_reasoning=feasibility_reasoning,
        objectives="\n".join(f"- {o}" for o in objectives) or "(none)",
        deliverables="\n".join(f"- {d}" for d in deliverables) or "(none)",
        stack="\n".join(
            f"- {s.category}: {s.technology} ({s.reasoning})" for s in stack
        )
        or "(none)",
        weeks="\n".join(
            f"Week {w.week}: " + "; ".join(w.tasks) for w in weeks
        )
        or "(none)",
        risks="\n".join(
            f"- [{r.likelihood}] {r.risk} (mitigation: {r.mitigation})" for r in risks
        )
        or "(none)",
    )


def run_mentor_agent(
    title: str,
    description: str,
    verdict: str,
    feasibility_reasoning: str,
    objectives: List[str],
    deliverables: List[str],
    stack: List[TechStackItem],
    weeks: List[WeekPlan],
    risks: List[RiskItem],
    history: List[Tuple[str, str]],
    new_message: str,
) -> str:
    """Runs one turn of the conversational mentor.

    `history` is a list of (role, content) tuples in chronological order,
    role being "student" or "mentor" (as stored in MentorMessage.role).
    Returns the mentor's plain-text reply - not persisted here, the caller
    (the router) writes both the student's message and this reply to the DB.
    """
    system_prompt = _build_system_prompt(
        title, description, verdict, feasibility_reasoning,
        objectives, deliverables, stack, weeks, risks,
    )

    contents = [
        types.Content(
            role="user" if role == "student" else "model",
            parts=[types.Part(text=content)],
        )
        for role, content in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=new_message)]))

    response = get_client().models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1024,
        ),
    )
    print(
        f"[mentor] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return response.text
