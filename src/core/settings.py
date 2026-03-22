"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Events Aggregator"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://localhost/events_aggregator"

    # Events Provider API
    events_provider_base_url: str = "http://events-provider.dev-2.python-labs.ru"
    events_provider_api_key: str = ""

    # Sync settings
    sync_interval_hours: int = 24  # Синхронизация раз в день

    @property
    def events_provider_events_url(self) -> str:
        """Get events endpoint URL."""
        return f"{self.events_provider_base_url}/api/events/"

    @property
    def events_provider_seats_url(self) -> str:
        """Get seats endpoint URL template."""
        return f"{self.events_provider_base_url}/api/events/{{event_id}}/seats/"

    @property
    def events_provider_register_url(self) -> str:
        """Get register endpoint URL template."""
        return f"{self.events_provider_base_url}/api/events/{{event_id}}/register/"

    @property
    def events_provider_unregister_url(self) -> str:
        """Get unregister endpoint URL template."""
        return f"{self.events_provider_base_url}/api/events/{{event_id}}/unregister/"


settings = Settings()
