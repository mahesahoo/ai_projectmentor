# ProjectIdea.status values for the Milestone 2/3 agent pipeline.
# Each stage flips status on entry so the frontend can poll /api/ideas/{id}
# and show which agent is currently running.
SUBMITTED = "submitted"
ANALYZING_FEASIBILITY = "analyzing_feasibility"
ANALYZING_SCOPE = "analyzing_scope"
ANALYZING_TECH = "analyzing_tech"
ANALYZING_TIMELINE = "analyzing_timeline"
ANALYZING_RISK = "analyzing_risk"  # Milestone 3
ANALYZED = "analyzed"
FAILED = "failed"
