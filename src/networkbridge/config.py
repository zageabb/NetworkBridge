from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETWORKBRIDGE_", extra="ignore")
    host: str = "127.0.0.1"
    port: int = 8765
    database_url: str = "sqlite:///./networkbridge.db"
    router_url: str = "https://192.168.1.254"
    router_tls_certificate: Path | None = None
    router_polling_enabled: bool = False
    wan_retention_days: int = Field(default=0, ge=0, le=3650)
    neighbour_discovery_enabled: bool = False
    device_alias_writes_enabled: bool = False
    active_discovery_enabled: bool = False
    active_discovery_cidr: str = ""
    memory_alert_percent: float = 85.0
    disk_alert_percent: float = 90.0
    static_dir: Path = Path(__file__).resolve().parents[2] / "ui" / "dist"


settings = Settings()
