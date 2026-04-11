"""
Confluence delivery — publishes Weekly Recap as a Confluence page.
Optional: only used when CONFLUENCE_URL is configured.
"""
import logging
from atlassian import Confluence

from ..config import get_settings
from ..models import WeeklyRecap

logger = logging.getLogger(__name__)


class ConfluenceDelivery:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.confluence_url:
            raise ValueError("CONFLUENCE_URL is not configured")
        self._client = Confluence(
            url=settings.confluence_url,
            username=settings.jira_email,
            password=settings.jira_api_token,
            cloud=True,
        )
        self._space_key = settings.confluence_space_key
        self._parent_page_id = settings.confluence_parent_page_id

    def publish_recap(self, recap: WeeklyRecap, markdown: str) -> bool:
        """
        Create or update a Confluence page with the weekly recap.
        Page title: "Sprint Recap — {sprint_name} — Week {week_end}"
        """
        title = (
            f"Sprint Recap — {recap.sprint_summary.sprint_name} — Week {recap.week_end}"
        )
        # Confluence uses XHTML storage format; wrap markdown in a code block for now
        body = f"<ac:structured-macro ac:name='markdown'><ac:plain-text-body><![CDATA[{markdown}]]></ac:plain-text-body></ac:structured-macro>"

        try:
            existing = self._client.get_page_by_title(self._space_key, title)
            if existing:
                page_id = existing["id"]
                self._client.update_page(
                    page_id=page_id,
                    title=title,
                    body=body,
                    parent_id=self._parent_page_id,
                )
                logger.info("Updated Confluence page: %s", title)
            else:
                self._client.create_page(
                    space=self._space_key,
                    title=title,
                    body=body,
                    parent_id=self._parent_page_id,
                )
                logger.info("Created Confluence page: %s", title)
            return True
        except Exception as exc:
            logger.error("Confluence publish failed: %s", exc)
            return False
