# Milestone 1: Step-by-Step Mentor Presentation Script

This script is structured strictly around **Task 1, Task 2, Task 3, and Task 4** in order, giving you a sequential talking guide for your mentor meeting.

---

## 🎙️ Introduction: Welcome & Overview
**Time target:** 1 minute

> **What to say:**
> "Good morning/afternoon, Sir/Ma'am. Today, I am presenting the completion of **Milestone 1** of my academic project: the **AI Academic Project Mentor** platform. 
> 
> The core goal of this milestone is to establish a secure, compliant, and robust database-driven foundation for student onboarding and project idea ingestion. By design, there is no AI or LLM logic in this build—it represents solid software engineering, ensuring our database schemas, security, and routes are fully validated before introducing the multi-agent AI pipeline in Milestone 2.
> 
> Let's go through the completed tasks one by one."

---

## 📚 TASK 1: Study Agentic AI Workflows
**Time target:** 2 minutes

*(You can reference your submitted requirements PDF: `Task1_Agentic_AI_Workflows_Requirements.md.pdf`)*

> **What to say:**
> "For **Task 1**, I studied agentic AI workflows and academic project mentoring methodologies. The core takeaways are:
> * **What is an AI Agent?** Unlike a static LLM, an AI agent is autonomous. It is given a system prompt defining its role, has access to tools (like searching the web, executing code, or writing database records), and operates in a feedback loop to achieve a specific goal.
> * **What is a Multi-Agent System?** It is a team of specialized agents working together. For our project, instead of asking one LLM to write a project blueprint, we delegate tasks to four distinct agents: a Feasibility Agent, a Scope Agent, a Planning Agent, and a Risk Agent.
> * **How do they communicate?** They communicate sequentially. The output of the Feasibility Agent (e.g. 'Project is feasible') is passed directly as context to the next agent (the Scope Agent), ensuring structured, reliable planning."

---

## 🎨 TASK 2: System Architecture & Database Designs
**Time target:** 3 minutes

*(Open the files in your `task2` folder one by one to show your mentor)*

> **What to say:**
> "For **Task 2**, I designed the complete system architecture, data models, and flowcharts. I have saved these as high-resolution SVGs in the `task2/` directory:
> 
> 1. **System Architecture (`01_system_architecture.svg`):** Shows the Student and Faculty web clients connecting to our REST API gateway. The API interacts with a background worker thread (to run the agent pipeline) and reads/writes to our relational database.
> 2. **Flowchart Student Journey (`03_flowchart_student_journey.svg`):** Maps the user experience. The student registers, logs in, fills out their profile details, performs a skill assessment, and submits their project idea, which triggers the backend queue.
> 3. **Entity-Relationship Model (`02_er_diagram.svg`):** Outlines the tables at a conceptual level, showing how students, skill ratings, and project ideas relate.
> 4. **Relational Database Design (`04_database_design.svg`):** This is our physical database schema design. It lists the exact SQL types (VARCHAR, INTEGER, TIMESTAMP) and constraints (Primary Keys, Foreign Keys, and Unique constraints) that we implemented in our database."

---

## 🔐 TASK 3: Student Onboarding & Profile Portal
**Time target:** 3 minutes

*(Open your browser at `http://localhost:8000` to demo, then open `app/auth.py` and `app/routers/profile.py` in your code editor)*

> **What to say:**
> "For **Task 3**, I implemented the secure student onboarding flow. Let's look at the implementation:
> * **Registration & Login:** On the web portal, a student registers and logs in. We do not store plain-text passwords. We use **PBKDF2-SHA256 password hashing** in `app/auth.py` for maximum database security.
> * **Stateless JWT Sessions:** Upon successful login, the server issues a signed JSON Web Token (JWT) with a 24-hour expiry. The client stores this token and attaches it to the HTTP Authorization headers.
> * **Profile & Skill Assessment Questionnaire:** Once logged in, the student completes their profile (branch and year) and rates their proficiency (Beginner, Intermediate, Advanced) across different tech stacks. Let me show you how this writes to the `skill_assessments` table in the database."

---

## 🚀 TASK 4: Project Idea Submission & Trigger Hook
**Time target:** 2 minutes

*(Demo submitting a project idea on the portal, and show the terminal log output)*

> **What to say:**
> "For **Task 4**, I implemented the project idea submission interface.
> * **Submission UI:** The student submits a project title and a 2-3 line description.
> * **Database Ingestion:** The API validates the fields using Pydantic schemas, saves it, and defaults the status to `"submitted"`. This status acts as the hook for Milestone 2.
> * **The Trigger Mechanism:** To satisfy the trigger requirement, I wired up an asynchronous **FastAPI Background Task** in `app/routers/ideas.py`. When I hit submit, the API returns instantly, and the server prints: `[Trigger Mechanism] Automatically triggering multi-agent pipeline for ProjectIdea...` to the console. This background task is fully ready to invoke our AI agent nodes in Milestone 2."

---

## 🧹 Key Engineering Highlight: DRY & SPA Refactoring
**Time target:** 1 minute

> **What to say:**
> "As an optimization step, I refactored the frontend to remove five duplicate HTML files. Instead of maintaining separate identical templates, we serve a single **`frontend/index.html`** SPA. I updated the FastAPI router to dynamically map page URLs to this unified file. This makes the frontend clean, lightweight, and 100% DRY (Don't Repeat Yourself)."

---

## 🙋‍♂️ Expected Q&A Preparation

* **Q: Why use SQLite and not Postgres/MySQL right now?**
  * *Answer:* "SQLite allows zero-configuration setup for local development. However, since we use SQLAlchemy ORM, the code is database-agnostic. We can migrate to PostgreSQL or MySQL instantly by setting the `DATABASE_URL` environment variable without changing any code."
* **Q: How does the background task help with the agent pipeline?**
  * *Answer:* "LLM agent pipelines take time to run (typically 5 to 15 seconds). Running them synchronously would block the server thread and freeze the frontend. By triggering it in a Background Task, the student gets an instant response, while the agents process the idea asynchronously."
