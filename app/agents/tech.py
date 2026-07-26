from typing import List, Tuple

from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import TechAgentOutput

SYSTEM_PROMPT = """You are the Technology Recommendation Agent in an AI Academic Project \
Mentor pipeline. You receive a student's project idea, its defined scope, and the student's \
self-reported skill assessments (tech stack + proficiency level).

Recommend a concrete technology stack:
- "stack": a list of items, each with a "category" (e.g. "frontend", "backend", "database", \
"ml/ai", "deployment"), a specific "technology" choice, and per-item "reasoning".
- "reasoning": one paragraph tying the choices together and explaining the overall strategy.

Weight recommendations toward technologies the student already has proficiency in where a \
reasonable choice exists - don't recommend an unfamiliar framework just because it's popular \
if the student's own skills point to a good alternative. Where the scope requires something \
outside the student's current skills, say so explicitly and note it's a learning curve, not a \
change of plan."""


def run_tech_agent(
    title: str,
    description: str,
    objectives: List[str],
    deliverables: List[str],
    skills: List[Tuple[str, str]],
) -> TechAgentOutput:
    skills_text = (
        "\n".join(f"- {tech_stack}: {proficiency}" for tech_stack, proficiency in skills)
        if skills
        else "(student has not submitted any skill assessments)"
    )
    user_content = (
        f"Project idea:\nTitle: {title}\nDescription: {description}\n\n"
        f"Scope objectives:\n" + "\n".join(f"- {o}" for o in objectives) + "\n\n"
        f"Scope deliverables:\n" + "\n".join(f"- {d}" for d in deliverables) + "\n\n"
        f"Student skill assessments:\n{skills_text}"
    )
    response = get_client().models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=TechAgentOutput.model_json_schema(),
            max_output_tokens=3000,
        ),
    )
    print(
        f"[tech] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return TechAgentOutput.model_validate_json(response.text)
