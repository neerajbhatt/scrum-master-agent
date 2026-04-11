SPRINT_STATUS_TOOL_PLAN = """To prepare the Sprint Status report, you need to call these tools:
1. get_active_sprint(board_id) — get sprint metadata and dates
2. get_sprint_issues(sprint_id) — get all issues with status/assignee/points
3. get_blockers(sprint_id, board_id) — get blocked/flagged items
4. get_team_workload(sprint_id) — get per-member assignment summary

Call all four. Use the sprint_id returned by get_active_sprint for the other tools."""

WEEKLY_RECAP_TOOL_PLAN = """To prepare the Weekly Recap, you need to call these tools:
1. get_active_sprint(board_id) — sprint metadata
2. get_sprint_issues(sprint_id) — full issue list
3. get_blockers(sprint_id, board_id) — blocked items
4. get_team_workload(sprint_id) — workload distribution
5. get_sprint_velocity(board_id, n_sprints=5) — historical velocity trend
6. get_sprint_burndown(sprint_id) — burndown approximation

Call all six tools. Use sprint_id from step 1 for steps 2-4 and 6."""
