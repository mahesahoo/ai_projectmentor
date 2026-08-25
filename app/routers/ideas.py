from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.agents.docs import run_docs_agent
from app.agents.mentor import run_mentor_agent
from app.agents.pipeline import run_pipeline
from app.agents.replan import run_replan_agent
from app.agents.risk import run_risk_agent
from app.database import SessionLocal, get_db
from app.models import (
    GeneratedDocument,
    MentorMessage,
    ProgressUpdate,
    RiskAssessment,
    Student,
    ProjectIdea,
    TimelinePlan,
)
from app.schemas import (
    BlueprintOut,
    DocumentGenerateIn,
    GeneratedDocumentOut,
    MentorMessageIn,
    MentorMessageOut,
    ProgressUpdateIn,
    ProgressUpdateOut,
    ProjectIdeaIn,
    ProjectIdeaOut,
    RiskItem,
    TechStackItem,
    WeekPlan,
)
from app.auth import get_current_student

router = APIRouter()


def _latest(rows):
    return max(rows, key=lambda r: r.created_at, default=None)


def _progress_notes(idea: ProjectIdea) -> List[str]:
    return [
        f"Week {p.week_number}: {p.update_text}" if p.week_number else p.update_text
        for p in idea.progress_updates
    ]


def _get_owned_idea(idea_id: str, db: Session, current_student: Student) -> ProjectIdea:
    idea = (
        db.query(ProjectIdea)
        .filter(
            ProjectIdea.idea_id == idea_id,
            ProjectIdea.student_id == current_student.student_id,
        )
        .first()
    )
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


def _call_agent(fn, *args, **kwargs):
    """Runs a synchronous agent call and turns any Gemini/upstream failure
    (rate limit, transient 503, missing key, etc.) into a clean 503 with a
    JSON body, instead of letting it bubble up as a bare 500 Internal Server
    Error. The background pipeline already has its own failure handling
    (sets idea.status = "failed"); these synchronous endpoints (chat, replan,
    documents) have no such status field to fall back on, so they need to
    fail cleanly right here instead.
    """
    try:
        return fn(*args, **kwargs)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="The AI mentor is temporarily unavailable (upstream API "
            "error). Please try again in a moment.",
        ) from exc


def trigger_agent_pipeline(idea_id: str):
    """BackgroundTasks entry point for the Milestone 2 agent pipeline.

    Opens its own DB session rather than reusing the request's session from
    Depends(get_db) - that session is closed as soon as the request handler
    returns, before this background task actually runs.
    """
    db = SessionLocal()
    try:
        run_pipeline(idea_id, db)
    finally:
        db.close()


@router.post("", response_model=ProjectIdeaOut, status_code=status.HTTP_201_CREATED)
def submit_idea(
    payload: ProjectIdeaIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    idea = ProjectIdea(
        student_id=current_student.student_id,
        title=payload.title,
        description=payload.description,
        # status defaults to "submitted" at the model level; the agent
        # pipeline below drives it through analyzing_* -> analyzed/failed.
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)

    # Milestone 1 Trigger Mechanism requirement, now wired to the real
    # Milestone 2 pipeline instead of the placeholder.
    background_tasks.add_task(trigger_agent_pipeline, idea.idea_id)

    return idea


@router.get("", response_model=List[ProjectIdeaOut])
def list_my_ideas(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    return (
        db.query(ProjectIdea)
        .filter(ProjectIdea.student_id == current_student.student_id)
        .order_by(ProjectIdea.submitted_at.desc())
        .all()
    )


@router.get("/{idea_id}", response_model=ProjectIdeaOut)
def get_idea(
    idea_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    return _get_owned_idea(idea_id, db, current_student)


@router.get("/{idea_id}/blueprint", response_model=BlueprintOut)
def get_blueprint(
    idea_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    idea = _get_owned_idea(idea_id, db, current_student)
    return {
        "idea": idea,
        "feasibility": _latest(idea.feasibility_reports),
        "scope": _latest(idea.scope_definitions),
        "tech": _latest(idea.tech_recommendations),
        "timeline": _latest(idea.timeline_plans),
        "risk": _latest(idea.risk_assessments),
    }


@router.get("/{idea_id}/chat", response_model=List[MentorMessageOut])
def get_chat_history(
    idea_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    idea = _get_owned_idea(idea_id, db, current_student)
    return idea.mentor_messages


@router.post("/{idea_id}/chat", response_model=MentorMessageOut)
def send_chat_message(
    idea_id: str,
    payload: MentorMessageIn,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """One turn of the Milestone 3 conversational mentor.

    Synchronous (not a BackgroundTask like the pipeline) - a chat message
    expects an immediate reply, there's no multi-stage progress to poll for.
    Gated on idea.status == "analyzed": the mentor's context is the finished
    blueprint, so chatting before the pipeline has produced one would mean
    grounding the conversation in nothing.
    """
    idea = _get_owned_idea(idea_id, db, current_student)
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

    student_msg = MentorMessage(idea_id=idea.idea_id, role="student", content=payload.content)
    db.add(student_msg)
    db.commit()

    history = [(m.role, m.content) for m in idea.mentor_messages[:-1]]
    reply_text = _call_agent(
        run_mentor_agent,
        idea.title,
        idea.description,
        feasibility.verdict if feasibility else "unknown",
        feasibility.reasoning if feasibility else "",
        scope.objectives if scope else [],
        scope.deliverables if scope else [],
        [TechStackItem(**item) for item in tech.stack] if tech else [],
        [WeekPlan(**week) for week in timeline.weeks] if timeline else [],
        [RiskItem(**item) for item in risk.risks] if risk else [],
        history,
        payload.content,
    )

    mentor_msg = MentorMessage(idea_id=idea.idea_id, role="mentor", content=reply_text)
    db.add(mentor_msg)
    db.commit()
    db.refresh(mentor_msg)
    return mentor_msg


@router.get("/{idea_id}/progress", response_model=List[ProgressUpdateOut])
def get_progress_history(
    idea_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    idea = _get_owned_idea(idea_id, db, current_student)
    return idea.progress_updates


@router.post("/{idea_id}/progress", response_model=ProgressUpdateOut, status_code=status.HTTP_201_CREATED)
def log_progress(
    idea_id: str,
    payload: ProgressUpdateIn,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Logs a progress update. No LLM call - this is a cheap DB write so the
    student can log freely; replanning (below) is the separate, explicit,
    costly action."""
    idea = _get_owned_idea(idea_id, db, current_student)
    if idea.status != "analyzed":
        raise HTTPException(
            status_code=409,
            detail="Log progress once the initial blueprint analysis is complete.",
        )
    update = ProgressUpdate(
        idea_id=idea.idea_id,
        week_number=payload.week_number,
        update_text=payload.update_text,
    )
    db.add(update)
    db.commit()
    db.refresh(update)
    return update


@router.post("/{idea_id}/replan", response_model=BlueprintOut)
def replan_idea(
    idea_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Re-runs Timeline + Risk agents with the original blueprint plus the
    full progress-update history as extra context, per the Milestone 3
    checklist decision. Persists new TimelinePlan/RiskAssessment rows rather
    than overwriting - GET /blueprint always returns the latest of each, so
    older plans stay in the DB as an audit trail.
    """
    idea = _get_owned_idea(idea_id, db, current_student)
    if idea.status != "analyzed":
        raise HTTPException(
            status_code=409,
            detail="The agent pipeline hasn't finished analyzing this idea yet.",
        )

    scope = _latest(idea.scope_definitions)
    tech = _latest(idea.tech_recommendations)
    timeline = _latest(idea.timeline_plans)
    if not (scope and tech and timeline):
        raise HTTPException(
            status_code=409,
            detail="Nothing to replan - this idea has no scope/timeline yet "
            "(it was likely marked not feasible).",
        )

    stack = [TechStackItem(**item) for item in tech.stack]
    original_weeks = [WeekPlan(**w) for w in timeline.weeks]
    progress_notes = _progress_notes(idea)

    new_timeline = _call_agent(
        run_replan_agent,
        idea.title, idea.description, scope.objectives, scope.deliverables,
        stack, original_weeks, progress_notes,
    )
    db.add(TimelinePlan(idea_id=idea.idea_id, weeks=[w.model_dump() for w in new_timeline.weeks]))
    db.commit()

    new_risk = _call_agent(
        run_risk_agent,
        idea.title, idea.description, scope.objectives, scope.deliverables,
        stack, new_timeline.weeks, progress_notes,
    )
    db.add(RiskAssessment(idea_id=idea.idea_id, risks=[r.model_dump() for r in new_risk.risks]))
    db.commit()

    db.refresh(idea)
    return {
        "idea": idea,
        "feasibility": _latest(idea.feasibility_reports),
        "scope": scope,
        "tech": tech,
        "timeline": _latest(idea.timeline_plans),
        "risk": _latest(idea.risk_assessments),
    }


@router.get("/{idea_id}/documents", response_model=List[GeneratedDocumentOut])
def get_documents(
    idea_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    idea = _get_owned_idea(idea_id, db, current_student)
    return idea.generated_documents


@router.post("/{idea_id}/documents", response_model=GeneratedDocumentOut)
def generate_document(
    idea_id: str,
    payload: DocumentGenerateIn,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Generates one Markdown document (synopsis/methodology/progress_report)
    on demand - never automatically, per the Milestone 3 brief's own wording.
    Persists a new row each time rather than overwriting (same audit-trail
    pattern as every other agent table)."""
    idea = _get_owned_idea(idea_id, db, current_student)
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

    content = _call_agent(
        run_docs_agent,
        payload.doc_type,
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
    )

    doc = GeneratedDocument(idea_id=idea.idea_id, doc_type=payload.doc_type, content=content)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
