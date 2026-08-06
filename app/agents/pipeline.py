from sqlalchemy.orm import Session

from app.agents import status
from app.agents.feasibility import run_feasibility_agent
from app.agents.risk import run_risk_agent
from app.agents.scope import run_scope_agent
from app.agents.tech import run_tech_agent
from app.agents.timeline import run_timeline_agent
from app.models import (
    FeasibilityReport,
    ProjectIdea,
    RiskAssessment,
    ScopeDefinition,
    SkillAssessment,
    TechRecommendation,
    TimelinePlan,
)


def run_pipeline(idea_id: str, db: Session) -> None:
    """Runs the Milestone 2/3 agent pipeline for one submitted idea.

    Called as a FastAPI BackgroundTask right after idea submission (see
    submit_idea in app/routers/ideas.py). Each stage persists its output and
    advances idea.status before the next stage starts, so the frontend can
    poll GET /api/ideas/{id} to see progress. Any Gemini API failure sets
    status to "failed" and stops the pipeline rather than continuing with a
    missing stage.
    """
    idea = db.query(ProjectIdea).filter(ProjectIdea.idea_id == idea_id).first()
    if idea is None:
        return

    try:
        idea.status = status.ANALYZING_FEASIBILITY
        db.commit()
        feasibility = run_feasibility_agent(idea.title, idea.description)
        db.add(
            FeasibilityReport(
                idea_id=idea.idea_id,
                verdict=feasibility.verdict,
                reasoning=feasibility.reasoning,
            )
        )
        db.commit()

        if feasibility.verdict == "not_feasible":
            # Nothing concrete to scope, recommend a stack for, or schedule -
            # continuing would force the Scope agent to invent a project the
            # student never actually proposed. Stop here; the mentor's
            # analysis (the feasibility report) is itself the useful output.
            idea.status = status.ANALYZED
            db.commit()
            return

        idea.status = status.ANALYZING_SCOPE
        db.commit()
        scope = run_scope_agent(
            idea.title,
            idea.description,
            feasibility.verdict,
            feasibility.reasoning,
        )
        db.add(
            ScopeDefinition(
                idea_id=idea.idea_id,
                objectives=scope.objectives,
                deliverables=scope.deliverables,
                out_of_scope=scope.out_of_scope,
            )
        )
        db.commit()

        idea.status = status.ANALYZING_TECH
        db.commit()
        skill_rows = (
            db.query(SkillAssessment)
            .filter(SkillAssessment.student_id == idea.student_id)
            .all()
        )
        skill_pairs = [(s.tech_stack, s.proficiency_level) for s in skill_rows]
        tech = run_tech_agent(
            idea.title,
            idea.description,
            scope.objectives,
            scope.deliverables,
            skill_pairs,
        )
        db.add(
            TechRecommendation(
                idea_id=idea.idea_id,
                stack=[item.model_dump() for item in tech.stack],
                reasoning=tech.reasoning,
            )
        )
        db.commit()

        idea.status = status.ANALYZING_TIMELINE
        db.commit()
        timeline = run_timeline_agent(
            idea.title,
            idea.description,
            scope.objectives,
            scope.deliverables,
            tech.stack,
        )
        db.add(
            TimelinePlan(
                idea_id=idea.idea_id,
                weeks=[week.model_dump() for week in timeline.weeks],
            )
        )
        db.commit()

        idea.status = status.ANALYZING_RISK
        db.commit()
        risk = run_risk_agent(
            idea.title,
            idea.description,
            scope.objectives,
            scope.deliverables,
            tech.stack,
            timeline.weeks,
        )
        db.add(
            RiskAssessment(
                idea_id=idea.idea_id,
                risks=[item.model_dump() for item in risk.risks],
            )
        )
        db.commit()

        idea.status = status.ANALYZED
        db.commit()

    except Exception as exc:
        # Broad on purpose: this runs as an unsupervised BackgroundTask, so
        # nothing else will ever see or handle an exception raised here -
        # not just anthropic.APIStatusError/APIConnectionError (a bad
        # request), but also e.g. a missing/invalid ANTHROPIC_API_KEY
        # (raised as a plain TypeError before any network call). Letting
        # any of these propagate would leave idea.status stuck on
        # whichever analyzing_* stage was running, silently, forever.
        db.rollback()
        idea.status = status.FAILED
        db.commit()
        print(f"[pipeline] agent pipeline failed for idea {idea_id}: {exc}")
