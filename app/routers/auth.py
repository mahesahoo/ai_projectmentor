from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.schemas import StudentRegister, StudentLogin, StudentOut, Token
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def register(payload: StudentRegister, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    student = Student(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        branch=payload.branch,
        year=payload.year,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.post("/login", response_model=Token)
def login(payload: StudentLogin, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.email == payload.email).first()
    if not student or not verify_password(payload.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": student.student_id})
    return {"access_token": token, "token_type": "bearer"}
