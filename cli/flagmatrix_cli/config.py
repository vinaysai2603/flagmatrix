"""Configuration file schema for FlagMatrix CLI (flagmatrix.yaml)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from flagmatrix_core import ManifestValidationError


class FlagsmithConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = "http://localhost:8000"
    api_key_env: str | None = None

    def resolve_api_key(
        self,
        explicit_key: str | None = None,
        target_url: str | None = None,
    ) -> str | None:
        if explicit_key:
            return explicit_key
        effective_url = (target_url or self.url).rstrip("/")
        configured_url = self.url.rstrip("/")
        parsed = urlparse(effective_url)
        host_key = f"FLAGSMITH_API_KEY_{parsed.netloc.replace(':', '_')}"
        sanitized_key = f"FLAGSMITH_API_KEY_{re.sub(r'[^A-Za-z0-9_]', '_', parsed.netloc)}"
        if os.environ.get(host_key):
            return os.environ[host_key]
        if os.environ.get(sanitized_key):
            return os.environ[sanitized_key]
        if effective_url == configured_url:
            if self.api_key_env and os.environ.get(self.api_key_env):
                return os.environ[self.api_key_env]
            return os.environ.get("FLAGSMITH_API_KEY")
        return None


class FlagMatrixConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    flagsmith: FlagsmithConfig = Field(default_factory=FlagsmithConfig)
    project_id: int = 1
    environment: str = "Development"
    profiles_path: str = "profiles"
    rules_path: str = "rules.yaml"
    strict: bool = False
    config_dir: Path | None = Field(default=None, exclude=True)

    def resolve_path(self, raw_path: str) -> Path:
        """Resolve a path relative to the directory containing flagmatrix.yaml."""
        candidate = Path(raw_path)
        if candidate.is_absolute() or self.config_dir is None:
            return candidate
        return (self.config_dir / candidate).resolve()


def load_config(path: Path) -> FlagMatrixConfig:
    resolved = path.resolve()
    if not resolved.exists():
        raise ManifestValidationError(path, "config file does not exist")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestValidationError(path, f"invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestValidationError(path, "config root must be a YAML mapping")
    try:
        cfg = FlagMatrixConfig.model_validate(raw)
    except ValidationError as exc:
        raise ManifestValidationError(path, str(exc)) from exc
    cfg.config_dir = resolved.parent
    return cfg
