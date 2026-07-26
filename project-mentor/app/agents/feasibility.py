from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import FeasibilityAgentOutput

SYSTEM_PROMPT = """You are the Feasibility Analysis Agent in an AI Academic Project Mentor \
pipeline. A student has submitted a rough project idea (2-3 lines). Assess whether it is a \
realistic academic project.

Return one of three verdicts:
- "feasible": realistic scope for a student to complete within a typical academic term.
- "risky": achievable but has notable risks - unclear scope, overly ambitious technology \
choices, unrealistic timeline, or missing detail that could derail execution.
- "not_feasible": not realistic as stated - scope is far too broad, requires resources or \
expertise a student is unlikely to have, or the idea has no real technical/academic substance.

Be an honest mentor, not a rubber stamp. A vague one-liner with no real technical content \
should be flagged, not waved through. Give reasoning in 2-4 sentences that a student could \
act on."""


def run_feasibility_agent(title: str, description: str) -> FeasibilityAgentOutput:
    response = get_client().models.generate_content(
        model=MODEL,
        contents=f"Project idea:\nTitle: {title}\nDescription: {description}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=FeasibilityAgentOutput.model_json_schema(),
            max_output_tokens=2048,
        ),
    )
    print(
        f"[feasibility] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return FeasibilityAgentOutput.model_validate_json(response.text)
