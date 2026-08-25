from typing import List

from google.genai import types

from app.agents.client import get_client, MODEL
from app.schemas import RiskItem, TechStackItem, WeekPlan

BASE_TEMPLATE = """You are the Documentation Generation Agent in an AI Academic Project \
Mentor pipeline. You are given a student's finished project blueprint (and progress log, if any). \
Generate ONE document: {doc_label}. Output raw Markdown only - no commentary before or after \
it, no "Here is your document:" preamble.

{doc_instructions}

Ground everything in the actual blueprint below - do not invent requirements, technologies, or \
deadlines that aren't in it.

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

Progress logged so far:
{progress}
=== END BLUEPRINT ==="""

DOC_INSTRUCTIONS = {
    "synopsis": (
        "Project Synopsis",
        "Write a formal academic project synopsis, ~300-500 words, mostly prose (not a bullet "
        "list), suitable to submit to a faculty mentor for project approval. Cover: the problem "
        "being addressed, the proposed solution/approach, and the expected outcome/deliverable. "
        "Use a level-1 Markdown heading with the project title, then the synopsis body.",
    ),
    "methodology": (
        "Methodology",
        "Write a technical methodology document describing HOW the project will be built: "
        "system architecture at a high level, why the recommended tech stack fits, the "
        "development approach (phase-by-phase, referencing the timeline), and how it will be "
        "tested/validated. Use Markdown headings and bullet points where useful - this is a "
        "technical reference document, not prose.",
    ),
    "progress_report": (
        "Progress Report",
        "Write a status report as of today: what's been completed, what's in progress or "
        "blocked, and what's planned next, based on the logged progress entries below. If no "
        "progress has been logged yet, say so explicitly and summarize the plan as it stands "
        "instead of fabricating completed work. Use Markdown headings: Completed, In Progress / "
        "Blocked, Next Steps.",
    ),
}


def run_docs_agent(
    doc_type: str,
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
) -> str:
    if doc_type not in DOC_INSTRUCTIONS:
        raise ValueError(f"Unknown doc_type: {doc_type}")
    doc_label, doc_instructions = DOC_INSTRUCTIONS[doc_type]

    system_prompt = BASE_TEMPLATE.format(
        doc_label=doc_label,
        doc_instructions=doc_instructions,
        title=title,
        description=description,
        verdict=verdict,
        feasibility_reasoning=feasibility_reasoning,
        objectives="\n".join(f"- {o}" for o in objectives) or "(none)",
        deliverables="\n".join(f"- {d}" for d in deliverables) or "(none)",
        stack="\n".join(f"- {s.category}: {s.technology} ({s.reasoning})" for s in stack)
        or "(none)",
        weeks="\n".join(f"Week {w.week}: " + "; ".join(w.tasks) for w in weeks) or "(none)",
        risks="\n".join(
            f"- [{r.likelihood}] {r.risk} (mitigation: {r.mitigation})" for r in risks
        )
        or "(none)",
        progress="\n".join(f"- {n}" for n in progress_notes) or "(no progress logged yet)",
    )

    response = get_client().models.generate_content(
        model=MODEL,
        contents=f"Generate the {doc_label} now.",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2500,
        ),
    )
    print(
        f"[docs:{doc_type}] tokens in={response.usage_metadata.prompt_token_count} "
        f"out={response.usage_metadata.candidates_token_count}"
    )
    return response.text
