from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Jira
    jira_url: str = Field(..., description="Jira base URL, e.g. https://myorg.atlassian.net")
    jira_email: str = Field(..., description="Jira account email")
    jira_api_token: str = Field(..., description="Atlassian API token")
    jira_board_id: int = Field(..., description="Default Jira board ID to monitor")

    # LLM
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    llm_model: str = "claude-sonnet-4-6"
    llm_temperature: float = 0.1

    # Slack
    slack_webhook_url: str = Field(..., description="Slack incoming webhook URL")
    slack_channel: str = "#sprint-updates"

    # Confluence (optional)
    confluence_url: Optional[str] = None
    confluence_space_key: Optional[str] = None
    confluence_parent_page_id: Optional[int] = None

    # MCP Server
    mcp_transport: str = "stdio"  # "stdio" | "sse"
    mcp_server_port: int = 8080

    # Scheduler
    recap_day: str = "fri"
    recap_hour: int = 17
    recap_minute: int = 0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
