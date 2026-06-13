\
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
    admin_token: str = os.getenv("ADMIN_TOKEN", "")

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    app_timezone: str = os.getenv("APP_TIMEZONE", "Europe/Istanbul")

    enable_daily_summary: bool = _bool_env("ENABLE_DAILY_SUMMARY", True)
    report_hour: int = _int_env("REPORT_HOUR", 9)
    report_minute: int = _int_env("REPORT_MINUTE", 0)

    database_path: str = os.getenv("DATABASE_PATH", "./data/signals.sqlite3")

    notify_on_first_signal: bool = _bool_env("NOTIFY_ON_FIRST_SIGNAL", False)
    notify_on_bar_close_snapshot: bool = _bool_env("NOTIFY_ON_BAR_CLOSE_SNAPSHOT", False)

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def webhook_configured(self) -> bool:
        return bool(self.webhook_secret)

    @property
    def admin_configured(self) -> bool:
        return bool(self.admin_token)


settings = Settings()
