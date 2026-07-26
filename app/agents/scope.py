from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import ScopeAgentOutput

SYSTEM_PROMPT = """You are the Scope Definition Agent in an AI Academic Project Mentor \
pipeline. You receive a student's project idea plus a feasibility verdict from the previous \
agent in the pipeline. Turn the rough idea into a concrete scope.

Produce:
- "objectives": 2-5 specific, measurable goals the project should achieve.
- "deliverables": concrete artifacts the student will hand in (e.g. "working REST API with \
auth", "trained classification model with >80% accuracy", "user-facing web dashboard").
- "out_of_scope": things students commonly assume are included but should explicitly be cut, \
given the feasibility verdict - especially if the verdict was "risky", be more aggressive \
about trimming scope here.

Keep everything concrete and specific to this idea - no generic filler like "good documentation" \
unless the idea specifically calls for it."""


def run_scope_agent(
    title: str,
    description: str,
    feasibility_verdict: str,
    feasibility_reasoning: str,
) -> ScopeAgentOutput:
    user_content = (
        f"Project idea:\nTitle: {title}\nDescription: {description}\n\n"
        f"Feasibility verdict: {feasibility_verdict}\n"
        f"Feasibility reasoning: {feasibility_reasoning}"
    )
    response = get_client().models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=ScopeAgentOutput.model_json_schema(),
            max_output_tokens=3000,
        ),
    )
    print(
        f"[scope] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return ScopeAgentOutput.model_validate_json(response.text)
