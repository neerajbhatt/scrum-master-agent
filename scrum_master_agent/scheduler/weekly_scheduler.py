"""
APScheduler-based scheduler for the Weekly Recap job.
Fires every Friday at the configured time (default 17:00).

Usage:
    python -m scrum_master_agent.scheduler.weekly_scheduler
    python -m scrum_master_agent.scheduler.weekly_scheduler --run-now
"""
import sys
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

from ..config import get_settings
from ..workflows.weekly_recap_workflow import run_weekly_recap

logger = logging.getLogger(__name__)


def weekly_recap_job() -> None:
    settings = get_settings()
    logger.info("Weekly recap job triggered for board_id=%d", settings.jira_board_id)
    try:
        recap = run_weekly_recap(
            board_id=settings.jira_board_id,
            delivery_target="slack",
        )
        if recap:
            logger.info("Weekly recap completed: %s", recap.sprint_summary.sprint_name)
        else:
            logger.error("Weekly recap returned no result")
    except Exception as exc:
        logger.exception("Weekly recap job failed: %s", exc)


def main():
    settings = get_settings()

    if "--run-now" in sys.argv:
        logger.info("Running weekly recap immediately (--run-now)")
        weekly_recap_job()
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(
        weekly_recap_job,
        trigger="cron",
        day_of_week=settings.recap_day,
        hour=settings.recap_hour,
        minute=settings.recap_minute,
        id="weekly_recap",
        name="Weekly Sprint Recap",
        replace_existing=True,
    )

    logger.info(
        "Scheduler started — weekly recap runs every %s at %02d:%02d",
        settings.recap_day.upper(),
        settings.recap_hour,
        settings.recap_minute,
    )
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
