import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Defaults to a local SQLite file so this runs with zero setup.
# To use PostgreSQL later, just set an env var, e.g.:
#   export DATABASE_URL="postgresql://user:password@localhost:5432/project_mentor"
# No code changes needed - the ORM models work identically on both.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./project_mentor.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
