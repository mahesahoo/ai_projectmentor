import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Student(Base):
    """Matches the STUDENT entity in the Task 2 ER diagram."""
    __tablename__ = "students"

    student_id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    branch = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    skill_assessments = relationship(
        "SkillAssessment", back_populates="student", cascade="all, delete-orphan"
    )
    project_ideas = relationship(
        "ProjectIdea", back_populates="student", cascade="all, delete-orphan"
    )


class SkillAssessment(Base):
    """Matches the SKILL_ASSESSMENT entity in the Task 2 ER diagram."""
    __tablename__ = "skill_assessments"

    assessment_id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False)
    tech_stack = Column(String, nullable=False)
    proficiency_level = Column(String, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="skill_assessments")


class ProjectIdea(Base):
    """Matches the PROJECT_IDEA entity in the Task 2 ER diagram.

    The `status` field defaults to "submitted" and is driven through the
    Milestone 2 pipeline stages defined in app/agents/status.py:
    submitted -> analyzing_feasibility -> analyzing_scope -> analyzing_tech
    -> analyzing_timeline -> analyzing_risk -> analyzed (or failed at any
    stage). The analyzing_risk stage was added in Milestone 3.
    """
    __tablename__ = "project_ideas"

    idea_id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, nullable=False, default="submitted")
    submitted_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="project_ideas")
    feasibility_reports = relationship(
        "FeasibilityReport", back_populates="idea", cascade="all, delete-orphan"
    )
    scope_definitions = relationship(
        "ScopeDefinition", back_populates="idea", cascade="all, delete-orphan"
    )
    tech_recommendations = relationship(
        "TechRecommendation", back_populates="idea", cascade="all, delete-orphan"
    )
    timeline_plans = relationship(
        "TimelinePlan", back_populates="idea", cascade="all, delete-orphan"
    )
    risk_assessments = relationship(
        "RiskAssessment", back_populates="idea", cascade="all, delete-orphan"
    )
    mentor_messages = relationship(
        "MentorMessage",
        back_populates="idea",
        cascade="all, delete-orphan",
        order_by="MentorMessage.created_at",
    )
    progress_updates = relationship(
        "ProgressUpdate",
        back_populates="idea",
        cascade="all, delete-orphan",
        order_by="ProgressUpdate.created_at",
    )
    generated_documents = relationship(
        "GeneratedDocument",
        back_populates="idea",
        cascade="all, delete-orphan",
        order_by="GeneratedDocument.created_at.desc()",
    )


class FeasibilityReport(Base):
    """Milestone 2 - Feasibility Analysis Agent output.

    One row per pipeline run (audit trail); the pipeline always reads the
    most recent row for a given idea_id.
    """
    __tablename__ = "feasibility_reports"

    report_id = Column(String, primary_key=True, default=gen_uuid)
    idea_id = Column(String, ForeignKey("project_ideas.idea_id"), nullable=False)
    verdict = Column(String, nullable=False)  # "feasible" | "risky" | "not_feasible"
    reasoning = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ProjectIdea", back_populates="feasibility_reports")


class ScopeDefinition(Base):
    """Milestone 2 - Scope Definition Agent output."""
    __tablename__ = "scope_definitions"

    scope_id = Column(String, primary_key=True, default=gen_uuid)
    idea_id = Column(String, ForeignKey("project_ideas.idea_id"), nullable=False)
    objectives = Column(JSON, nullable=False)  # list[str]
    deliverables = Column(JSON, nullable=False)  # list[str]
    out_of_scope = Column(JSON, nullable=False)  # list[str]
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ProjectIdea", back_populates="scope_definitions")


class TechRecommendation(Base):
    """Milestone 2 - Technology Recommendation Agent output."""
    __tablename__ = "tech_recommendations"

    recommendation_id = Column(String, primary_key=True, default=gen_uuid)
    idea_id = Column(String, ForeignKey("project_ideas.idea_id"), nullable=False)
    stack = Column(JSON, nullable=False)  # list[{"category", "technology", "reasoning"}]
    reasoning = Column(String, nullable=False)  # overall rationale
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ProjectIdea", back_populates="tech_recommendations")


class TimelinePlan(Base):
    """Milestone 2 - Timeline Planning Agent output."""
    __tablename__ = "timeline_plans"

    plan_id = Column(String, primary_key=True, default=gen_uuid)
    idea_id = Column(String, ForeignKey("project_ideas.idea_id"), nullable=False)
    weeks = Column(JSON, nullable=False)  # list[{"week": int, "tasks": list[str]}]
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ProjectIdea", back_populates="timeline_plans")


class RiskAssessment(Base):
    """Milestone 3 - Risk Assessment and Mitigation Agent output.

    Last stage of the blueprint pipeline: reads the full blueprint so far
    (idea + scope + tech + timeline) and flags what's likely to go wrong.
    """
    __tablename__ = "risk_assessments"

    assessment_id = Column(String, primary_key=True, default=gen_uuid)
    idea_id = Column(String, ForeignKey("project_ideas.idea_id"), nullable=False)
    risks = Column(JSON, nullable=False)  # list[{"risk", "likelihood", "mitigation"}]
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ProjectIdea", back_populates="risk_assessments")


class MentorMessage(Base):
    """Milestone 3 - Conversational Mentor module.

    Flat message log, one row per turn - a single thread per idea (no
    separate Conversation table needed at this scale). role is "student" or
    "mentor"; the mentor's system prompt and reply are grounded in the
    idea's finished blueprint (see app/agents/mentor.py), not persisted here.
    """
    __tablename__ = "mentor_messages"

    message_id = Column(String, primary_key=True, default=gen_uuid)
    idea_id = Column(String, ForeignKey("project_ideas.idea_id"), nullable=False)
    role = Column(String, nullable=False)  # "student" | "mentor"
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ProjectIdea", back_populates="mentor_messages")


class ProgressUpdate(Base):
    """Milestone 3 - Progress tracking.

    A cheap, LLM-free log entry the student writes to record status ("week 2:
    behind schedule on auth"). Logging is separate from replanning (see
    POST /api/ideas/{id}/replan) so the student can log freely without
    triggering an agent rerun every time.
    """
    __tablename__ = "progress_updates"

    update_id = Column(String, primary_key=True, default=gen_uuid)
    idea_id = Column(String, ForeignKey("project_ideas.idea_id"), nullable=False)
    week_number = Column(Integer, nullable=True)
    update_text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ProjectIdea", back_populates="progress_updates")


class GeneratedDocument(Base):
    """Milestone 3 - on-demand documentation generation.

    Persisted per generation (not overwritten) so a student/faculty can look
    at past versions instead of losing them on regenerate - same audit-trail
    reasoning as every other agent table in this app.
    """
    __tablename__ = "generated_documents"

    document_id = Column(String, primary_key=True, default=gen_uuid)
    idea_id = Column(String, ForeignKey("project_ideas.idea_id"), nullable=False)
    doc_type = Column(String, nullable=False)  # "synopsis" | "methodology" | "progress_report"
    content = Column(String, nullable=False)  # Markdown
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ProjectIdea", back_populates="generated_documents")
