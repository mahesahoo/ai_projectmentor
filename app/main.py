from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.routers import auth, profile, ideas, faculty

# Creates tables on startup if they don't exist yet (fine for Milestone 1;
# swap to Alembic migrations once the schema stabilizes in later milestones).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Academic Project Mentor - Milestone 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(ideas.router, prefix="/api/ideas", tags=["ideas"])
app.include_router(faculty.router, prefix="/api/faculty", tags=["faculty"])

from fastapi.responses import FileResponse

@app.get("/login.html", include_in_schema=False)
@app.get("/register.html", include_in_schema=False)
@app.get("/profile.html", include_in_schema=False)
@app.get("/skill_assessment.html", include_in_schema=False)
@app.get("/submit_idea.html", include_in_schema=False)
@app.get("/faculty.html", include_in_schema=False)
def serve_spa():
    return FileResponse("frontend/index.html")

# Serves frontend/index.html, register.html, etc. directly.
# Mounted last and at "/" so it doesn't shadow the /api/* routes above.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
