from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    env: str = "dev"
    db_url: str = "sqlite:///./lostdog.db"
    evidence_dir: str = "./data/evidence"
    cases_dir: str = "./data/cases"
    screenshot_dir: str = "./data/screenshots"
    enable_browser_session: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            env=os.getenv("LOSTDOG_ENV", "dev"),
            db_url=os.getenv("LOSTDOG_DB_URL", "sqlite:///./lostdog.db"),
            evidence_dir=os.getenv("LOSTDOG_EVIDENCE_DIR", "./data/evidence"),
            cases_dir=os.getenv("LOSTDOG_CASES_DIR", "./data/cases"),
            screenshot_dir=os.getenv("LOSTDOG_SCREENSHOT_DIR", "./data/screenshots"),
            enable_browser_session=os.getenv(
                "LOSTDOG_ENABLE_BROWSER_SESSION", "false"
            ).lower()
            in {"1", "true", "yes", "on"},
        )
