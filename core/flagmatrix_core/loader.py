"""YAML and JSON loaders with explicit schema validation errors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from flagmatrix_core.models import ApplicationProfile, RuleSet


class ManifestValidationError(ValueError):
    """Raised when a manifest or rule file is malformed or fails schema validation."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        super().__init__(f"{path}: {message}")


def _load_structured_file(path: Path) -> Any:
    if not path.exists():
        raise ManifestValidationError(path, "file does not exist")
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ManifestValidationError(path, f"invalid YAML syntax: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestValidationError(path, "root document must be a YAML/JSON mapping")
    return data


def _format_pydantic_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


def load_profile(path: Path) -> ApplicationProfile:
    """Load and validate a single ApplicationProfile manifest."""
    data = _load_structured_file(path)
    try:
        return ApplicationProfile.model_validate(data)
    except ValidationError as exc:
        raise ManifestValidationError(path, _format_pydantic_error(exc)) from exc


def load_profiles(path_or_dir: Path) -> list[ApplicationProfile]:
    """Load one profile file or all *.yaml/*.yml/*.json profiles in a directory."""
    if path_or_dir.is_file():
        return [load_profile(path_or_dir)]
    if not path_or_dir.is_dir():
        raise ManifestValidationError(path_or_dir, "path is neither a file nor a directory")
    files = sorted(
        p
        for p in path_or_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".yaml", ".yml", ".json"}
    )
    if not files:
        raise ManifestValidationError(path_or_dir, "no profile files (*.yaml, *.yml, *.json) found")
    return [load_profile(f) for f in files]


def load_ruleset(path: Path) -> RuleSet:
    """Load and validate a FeatureRule RuleSet."""
    data = _load_structured_file(path)
    try:
        return RuleSet.model_validate(data)
    except ValidationError as exc:
        raise ManifestValidationError(path, _format_pydantic_error(exc)) from exc
