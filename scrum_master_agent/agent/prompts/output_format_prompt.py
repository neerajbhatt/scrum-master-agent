SPRINT_STATUS_FORMAT = """
Based on the tool results provided, generate a Sprint Status report in this exact Markdown format:

## Sprint Status: {sprint_name}
**As of:** {timestamp}  |  **Days Remaining:** {days_remaining}  |  **Goal:** {goal}

### Progress
- Total Issues: {total} | Done: {done} ({done_pct}%) | In Progress: {in_prog} | Blocked: {blocked}
- Story Points: {done_pts}/{total_pts} ({pts_pct}% complete)

### Blockers ({blocker_count})
| Issue | Summary | Assignee | Days Blocked | Severity | Suggested Action |
|-------|---------|----------|--------------|----------|-----------------|
{blocker_rows}

### Team Workload
| Member | Assigned | Done | In Progress | Points Done/Total |
|--------|----------|------|-------------|-------------------|
{team_rows}

### Risk Assessment
{2-3 concise risks derived from the data, e.g. low velocity, many blockers, unbalanced workload}
"""

WEEKLY_RECAP_FORMAT = """
Based on the tool results provided, generate a Weekly Recap in this exact Markdown format:

## Weekly Recap — {sprint_name} | Week ending {week_end}

**Executive Summary:** {2-3 sentence summary of sprint health, key accomplishments, and main risks}

### What We Accomplished
{bullet list of completed stories/tasks with story points}

### Blockers & Impediments
{table or bullet list of blockers with severity and resolution status}

### Velocity & Trend
{table of last N sprints: Sprint | Committed | Completed | Velocity%}
{one sentence trend commentary}

### Risks & Recommendations
{numbered list of risks with recommended actions}

### Next Week Focus
{2-3 priority items for the upcoming week based on remaining work and sprint goal}
"""
