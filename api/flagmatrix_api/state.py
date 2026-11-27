"""In-memory session store for FlagMatrix FastAPI adapter."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from flagmatrix_core import (
    ApplicationProfile,
    CoverageSummary,
    FlagsmithClient,
    RuleSet,
    ValidationReport,
    load_profiles,
    load_ruleset,
)


class ValidationRecord(BaseModel):
    run_id: str
    created_at: str
    report: ValidationReport
    coverage: CoverageSummary


class AppState:
    """Holds Flagsmith connection settings, loaded profiles/rules, and validation history."""

    def __init__(self) -> None:
        self.flagsmith_url: str = os.environ.get("FLAGSMITH_API_URL", "http://localhost:8000")
        self.flagsmith_api_key: str | None = (
            os.environ.get("FLAGSMITH_API_KEY_localhost_8000")
            or os.environ.get("FLAGSMITH_API_KEY")
        )
        self.profiles: list[ApplicationProfile] = []
        self.ruleset: RuleSet = RuleSet(schema_version="1.0", rules=[])
        self.history: dict[str, ValidationRecord] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        root = Path(__file__).resolve().parents[2]
        profiles_dir = root / "examples" / "profiles"
        rules_file = root / "examples" / "rules.yaml"
        if profiles_dir.is_dir():
            try:
                self.profiles = load_profiles(profiles_dir)
            except Exception:
                self.profiles = []
        if rules_file.is_file():
            try:
                self.ruleset = load_ruleset(rules_file)
            except Exception:
                self.ruleset = RuleSet(schema_version="1.0", rules=[])

    def get_client(self) -> FlagsmithClient:
        return FlagsmithClient(base_url=self.flagsmith_url, api_key=self.flagsmith_api_key)

    def save_run(self, report: ValidationReport, coverage: CoverageSummary) -> ValidationRecord:
        record = ValidationRecord(
            run_id=report.run_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            report=report,
            coverage=coverage,
        )
        self.history[report.run_id] = record
        return record
