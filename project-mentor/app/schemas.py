from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class StudentRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    branch: Optional[str] = None
    year: Optional[int] = None


class StudentLogin(BaseModel):
    email: EmailStr
    password: str


class StudentOut(BaseModel):
    student_id: str
    name: str
    email: str
    branch: Optional[str] = None
    year: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None
    year: Optional[int] = None


class SkillAssessmentIn(BaseModel):
    tech_stack: str
    proficiency_level: str


class SkillAssessmentOut(BaseModel):
    assessment_id: str
    tech_stack: str
    proficiency_level: str
    submitted_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectIdeaIn(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class ProjectIdeaOut(BaseModel):
    idea_id: str
    title: str
    description: str
    status: str
    submitted_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Milestone 2 - agent pipeline
#
# Each "*AgentOutput" schema is passed to client.messages.parse(output_format=...)
# so the LLM's response is constrained to exactly this shape - it doubles as
# the DB-write payload. Each "*Out" schema is the API response shape (adds the
# DB-only fields: id, idea_id, created_at).
# ---------------------------------------------------------------------------


class FeasibilityAgentOutput(BaseModel):
    verdict: Literal["feasible", "risky", "not_feasible"]
    reasoning: str


class FeasibilityReportOut(BaseModel):
    report_id: str
    idea_id: str
    verdict: str
    reasoning: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScopeAgentOutput(BaseModel):
    objectives: List[str]
    deliverables: List[str]
    out_of_scope: List[str]


class ScopeDefinitionOut(BaseModel):
    scope_id: str
    idea_id: str
    objectives: List[str]
    deliverables: List[str]
    out_of_scope: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TechStackItem(BaseModel):
    category: str  # e.g. "frontend", "backend", "database"
    technology: str
    reasoning: str


class TechAgentOutput(BaseModel):
    stack: List[TechStackItem]
    reasoning: str  # overall rationale tying the stack together


class TechRecommendationOut(BaseModel):
    recommendation_id: str
    idea_id: str
    stack: List[TechStackItem]
    reasoning: str
    created_at: datetime

    class Config:
        from_attributes = True


class WeekPlan(BaseModel):
    week: int
    tasks: List[str]


class TimelineAgentOutput(BaseModel):
    weeks: List[WeekPlan]


class TimelinePlanOut(BaseModel):
    plan_id: str
    idea_id: str
    weeks: List[WeekPlan]
    created_at: datetime

    class Config:
        from_attributes = True


class BlueprintOut(BaseModel):
    """Aggregated view of an idea plus its latest agent outputs, for
    GET /api/ideas/{id}/blueprint. Any stage not yet run (or still in
    progress) is null rather than the endpoint erroring."""

    idea: ProjectIdeaOut
    feasibility: Optional[FeasibilityReportOut] = None
    scope: Optional[ScopeDefinitionOut] = None
    tech: Optional[TechRecommendationOut] = None
    timeline: Optional[TimelinePlanOut] = None

    class Config:
        from_attributes = True
