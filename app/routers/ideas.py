from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.agents.pipeline import run_pipeline
from app.database import SessionLocal, get_db
from app.models import Student, ProjectIdea
from app.schemas import BlueprintOut, ProjectIdeaIn, ProjectIdeaOut
from app.auth import get_current_student

router = APIRouter()


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


@router.get("/{idea_id}/blueprint", response_model=BlueprintOut)
def get_blueprint(
    idea_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
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

    def latest(rows):
        return max(rows, key=lambda r: r.created_at, default=None)

    return {
        "idea": idea,
        "feasibility": latest(idea.feasibility_reports),
        "scope": latest(idea.scope_definitions),
        "tech": latest(idea.tech_recommendations),
        "timeline": latest(idea.timeline_plans),
    }
