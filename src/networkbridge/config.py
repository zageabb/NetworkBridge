from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETWORKBRIDGE_", extra="ignore")
    host: str = "127.0.0.1"
    port: int = 8765
    database_url: str = "sqlite:///./networkbridge.db"
    router_url: str = "https://192.168.1.254"
    router_polling_enabled: bool = False
    neighbour_discovery_enabled: bool = False
    active_discovery_enabled: bool = False
    active_discovery_cidr: str = ""
    memory_alert_percent: float = 85.0
    disk_alert_percent: float = 90.0
    static_dir: Path = Path(__file__).resolve().parents[2] / "ui" / "dist"


settings = Settings()
