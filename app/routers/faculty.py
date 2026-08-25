from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.faculty_summary import run_faculty_summary_agent
from app.auth import get_current_faculty
from app.database import get_db
from app.models import ProjectIdea, ProjectSummary, Student
from app.routers.ideas import _call_agent, _latest, _progress_notes
from app.schemas import (
    DashboardProjectOut,
    FacultyIdeaDetailOut,
    ProjectSummaryOut,
    RiskItem,
    TechStackItem,
    WeekPlan,
)

router = APIRouter()


def _compute_health_indicators(idea: ProjectIdea) -> dict:
    """Milestone 4 - faculty dashboard health indicators, computed straight
    from already-persisted data (no LLM call - see MILESTONE4_CHECKLIST.md
    step 6 for why each field is derived the way it is).

    Takes an already-loaded ProjectIdea (with its relationships available -
    the caller is responsible for the query, this function does no querying
    of its own) and returns a plain dict matching the non-summary fields of
    DashboardProjectOut.
    """
    feasibility = _latest(idea.feasibility_reports)
    timeline = _latest(idea.timeline_plans)
    risk = _latest(idea.risk_assessments)

    # weeks_completed: deliberately NOT parsed from TimelinePlan.weeks[].tasks
    # text (e.g. sniffing for a "Completed:" prefix) - that prefix is prose
    # the replan agent happens to write, not a structured field, and only
    # exists after a replan has run at least once. ProgressUpdate.week_number
    # is structured, student-supplied, and available from week 1 onward.
    week_numbers = [p.week_number for p in idea.progress_updates if p.week_number is not None]
    weeks_completed = max(week_numbers, default=0)
    weeks_total = len(timeline.weeks) if timeline else None

    high_risk_count = 0
    if risk:
        high_risk_count = sum(
            1 for item in risk.risks if RiskItem(**item).likelihood == "high"
        )

    # First TimelinePlan row is the original pipeline run, not a replan - see
    # checklist step 6 for the note on why this can drift from RiskAssessment's
    # row count if a replan's second (risk) call fails after the first
    # (timeline) call already committed.
    replan_count = max(len(idea.timeline_plans) - 1, 0)

    days_since_last_progress: Optional[int] = None
    if idea.progress_updates:
        # relationship is ordered by created_at ascending - last element is newest
        last_update = idea.progress_updates[-1]
        days_since_last_progress = (datetime.utcnow() - last_update.created_at).days

    # Student-authored turns only - "how many times has the student engaged
    # the mentor", not every row (which double-counts with the mentor's replies).
    chat_message_count = sum(1 for m in idea.mentor_messages if m.role == "student")

    return {
        "verdict": feasibility.verdict if feasibility else None,
        "weeks_completed": weeks_completed,
        "weeks_total": weeks_total,
        "high_risk_count": high_risk_count,
        "replan_count": replan_count,
        "days_since_last_progress": days_since_last_progress,
        "chat_message_count": chat_message_count,
    }


def _get_any_idea(idea_id: str, db: Session) -> ProjectIdea:
    """Same 404-if-missing shape as ideas.py's _get_owned_idea, but with no
    ownership filter - the whole point of the faculty router is crossing
    student boundaries, gated by get_current_faculty instead."""
    idea = db.query(ProjectIdea).filter(ProjectIdea.idea_id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.get("/dashboard", response_model=List[DashboardProjectOut])
def get_dashboard(
    db: Session = Depends(get_db),
    current_faculty: Student = Depends(get_current_faculty),
):
    """Lists every student's every idea with computed health indicators and
    the latest generated summary, if any. Never generates a summary itself -
    that's the separate, explicit POST below (same cost discipline as
    Milestone 3's replan: cheap to view, costly action stays deliberate)."""
    ideas = db.query(ProjectIdea).all()
    rows = []
    for idea in ideas:
        rows.append(
            {
                "idea": idea,
                "student_name": idea.student.name,
                "student_email": idea.student.email,
                "latest_summary": _latest(idea.project_summaries),
                **_compute_health_indicators(idea),
            }
        )
    return rows


@router.post("/ideas/{idea_id}/summary", response_model=ProjectSummaryOut)
def generate_project_summary(
    idea_id: str,
    db: Session = Depends(get_db),
    current_faculty: Student = Depends(get_current_faculty),
):
    """Explicit trigger to (re)generate one idea's ProjectSummary. Gated on
    status == "analyzed" - same as chat/replan/documents in ideas.py - since
    that's the point a blueprint (however thin, for a not_feasible idea)
    actually exists to summarize."""
    idea = _get_any_idea(idea_id, db)
    if idea.status != "analyzed":
        raise HTTPException(
            status_code=409,
            detail="The agent pipeline hasn't finished analyzing this idea yet.",
        )

    feasibility = _latest(idea.feasibility_reports)
    scope = _latest(idea.scope_definitions)
    tech = _latest(idea.tech_recommendations)
    timeline = _latest(idea.timeline_plans)
    risk = _latest(idea.risk_assessments)
    indicators = _compute_health_indicators(idea)

    result = _call_agent(
        run_faculty_summary_agent,
        idea.title,
        idea.description,
        feasibility.verdict if feasibility else "unknown",
        feasibility.reasoning if feasibility else "",
        scope.objectives if scope else [],
        scope.deliverables if scope else [],
        [TechStackItem(**item) for item in tech.stack] if tech else [],
        [WeekPlan(**week) for week in timeline.weeks] if timeline else [],
        [RiskItem(**item) for item in risk.risks] if risk else [],
        _progress_notes(idea),
        indicators["replan_count"],
        indicators["chat_message_count"],
    )

    summary = ProjectSummary(
        idea_id=idea.idea_id, summary=result.summary, health_status=result.health_status
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


@router.get("/ideas/{idea_id}", response_model=FacultyIdeaDetailOut)
def get_faculty_idea_detail(
    idea_id: str,
    db: Session = Depends(get_db),
    current_faculty: Student = Depends(get_current_faculty),
):
    """Single-idea drill-down for when a faculty member clicks into one
    project from the dashboard list: full blueprint + progress + chat
    history + latest summary."""
    idea = _get_any_idea(idea_id, db)
    return {
        "idea": idea,
        "student_name": idea.student.name,
        "student_email": idea.student.email,
        "feasibility": _latest(idea.feasibility_reports),
        "scope": _latest(idea.scope_definitions),
        "tech": _latest(idea.tech_recommendations),
        "timeline": _latest(idea.timeline_plans),
        "risk": _latest(idea.risk_assessments),
        "progress_updates": idea.progress_updates,
        "chat_messages": idea.mentor_messages,
        "latest_summary": _latest(idea.project_summaries),
    }
