from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student, SkillAssessment
from app.schemas import StudentOut, StudentUpdate, SkillAssessmentIn, SkillAssessmentOut
from app.auth import get_current_student

router = APIRouter()


@router.get("/me", response_model=StudentOut)
def get_my_profile(current_student: Student = Depends(get_current_student)):
    return current_student


@router.put("/me", response_model=StudentOut)
def update_my_profile(
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    if payload.name is not None:
        current_student.name = payload.name
    if payload.branch is not None:
        current_student.branch = payload.branch
    if payload.year is not None:
        current_student.year = payload.year
    db.commit()
    db.refresh(current_student)
    return current_student


@router.post("/me/skills", response_model=SkillAssessmentOut, status_code=201)
def add_skill_assessment(
    payload: SkillAssessmentIn,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    assessment = SkillAssessment(
        student_id=current_student.student_id,
        tech_stack=payload.tech_stack,
        proficiency_level=payload.proficiency_level,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/me/skills", response_model=List[SkillAssessmentOut])
def get_my_skill_assessments(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    return (
        db.query(SkillAssessment)
        .filter(SkillAssessment.student_id == current_student.student_id)
        .all()
    )
