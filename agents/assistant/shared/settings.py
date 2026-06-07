from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration values for the application.

    Pydantic reads these automatically from environment variables (or a .env file).
    The variable names map directly to the field names in uppercase, e.g.
    the field `ms_client_id` is read from the environment variable `MS_CLIENT_ID`.

    Fields without a default value are required — the app will refuse to start
    if they are missing.
    """

    model_config = {"env_file": ".env"}

    ms_client_id: str
    """The client ID of your Microsoft Entra (Azure AD) app registration."""

    ms_client_secret: str
    """The client secret of your Microsoft Entra app registration."""

    ms_redirect_uri: str = "http://localhost:8000/auth/microsoft/callback"
    """The URL Microsoft redirects to after the user logs in. Must match what is
    registered in the Azure portal."""

    ms_tenant: str = "consumers"
    """The Microsoft tenant to authenticate against. 'consumers' covers personal
    Microsoft/Outlook accounts."""

    aws_region: str = "eu-central-1"
    """The AWS region where the Bedrock model is available."""

    bedrock_model_id: str = "eu.amazon.nova-2-lite-v1:0"
    """The Amazon Bedrock model ID used for email triage and drafting."""

    user_name: str = "Adel"
    """The name of the user the assistant is working for. Used in LLM prompts."""

    mcp_memory_url: str | None = None
    """The SSE endpoint of the MCP memory server, e.g. 'http://ec2-ip:3000/sse'.
    When set, the agent queries this server for personal context before each
    email assessment. Leave unset to disable memory lookups."""

    mcp_memory_client_id: str | None = None

    mcp_memory_refresh_token: str | None = None

    # Job hunting agent
    database_url: str | None = None
    """PostgreSQL DSN for the job_matches table, e.g. postgresql://user:pass@localhost/adel_intelligence.
    If not set directly, assembled from DB_HOST / DB_USER / DB_PASSWORD / DB_NAME / DB_PORT."""

    # Individual DB connection components — read from DB_HOST, DB_USER, etc.
    # Used to assemble database_url when it is not provided as a full DSN.
    db_host: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_name: str = "postgres"
    db_port: int = 5432

    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
        if self.database_url is None and all(
            [self.db_host, self.db_user, self.db_password]
        ):
            self.database_url = (
                f"postgresql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self

    rapidapi_key: str | None = None
    """RapidAPI key for the JSearch / LinkedIn Jobs Search API."""

    rapidapi_host: str = "jsearch.p.rapidapi.com"
    """RapidAPI host header — override to 'linkedin-jobs-search.p.rapidapi.com' if using that API."""

    scraper_delay_seconds: float = 2.0
    """Seconds to wait between page requests to avoid rate-limiting."""

    scraper_max_results_per_query: int = 20
    """Maximum job listings to collect per search query."""

    notification_email: str = "adel.haidar@outlook.com"
    """Email address to notify when strong matches are found."""


@lru_cache
def get_settings() -> Settings:
    """Return the application settings, reading from environment variables once and caching the result.

    The `@lru_cache` decorator means this function only does the actual work on
    the first call. Every subsequent call returns the same cached object instantly,
    so environment variables are only read once at startup.
    """
    return Settings()
