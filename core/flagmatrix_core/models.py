"""Pydantic models for application capability manifests, rules, and findings."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from flagmatrix_core.semver import MalformedVersionError, parse_semver

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
SUPPORTED_PLATFORMS = {"android", "ios", "web", "windows", "macos", "linux"}


class EvaluationStatus(str, Enum):
    """Deterministic outcome of a compatibility check."""

    PASS = "PASS"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"
    SKIPPED = "SKIPPED"


class ApplicationProfile(BaseModel):
    """Versioned manifest declaring an application build's capabilities."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    app_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    platform: str
    app_version: str
    build_flavor: str = "production"
    environment: str = Field(..., min_length=1)
    installed_sdks: list[str] = Field(default_factory=list)
    sdk_versions: dict[str, str] = Field(default_factory=dict)
    native_resources: dict[str, Any] = Field(default_factory=dict)
    backend_api_versions: dict[str, str] = Field(default_factory=dict)
    device_capabilities: dict[str, Any] = Field(default_factory=dict)
    identity_traits: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        if value not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"Unsupported manifest schema_version {value!r}; "
                f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )
        return value

    @field_validator("platform")
    @classmethod
    def _validate_platform(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Unsupported platform {value!r}; "
                f"supported: {sorted(SUPPORTED_PLATFORMS)}"
            )
        return normalized

    @field_validator("app_version")
    @classmethod
    def _validate_app_version(cls, value: str) -> str:
        parse_semver(value)
        return value

    @field_validator("sdk_versions", "backend_api_versions")
    @classmethod
    def _validate_version_maps(cls, value: dict[str, str]) -> dict[str, str]:
        for name, ver in value.items():
            try:
                parse_semver(ver)
            except MalformedVersionError as exc:
                raise ValueError(f"Invalid version for {name!r}: {exc}") from exc
        return value

    @property
    def profile_id(self) -> str:
        return f"{self.tenant_id}:{self.app_id}:{self.platform}:{self.app_version}"

    def all_installed_sdks(self) -> set[str]:
        return set(self.installed_sdks) | set(self.sdk_versions.keys())


class FlagValueState(BaseModel):
    """Evaluated feature flag state for a specific identity or environment."""

    feature_name: str
    enabled: bool
    value: Any = None
    source: Literal["flagsmith", "hypothetical"] = "flagsmith"
    identity: str | None = None


ConstraintType = Literal[
    "sdk_installed",
    "sdk_version",
    "backend_api_version",
    "native_resource",
    "device_capability",
    "app_version",
    "flag_value",
    "platform_in",
    "incompatible_with",
]


class CapabilityConstraint(BaseModel):
    """Single deterministic constraint required by a feature rule."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    type: ConstraintType
    target: str = Field(..., min_length=1)
    min_version: str | None = None
    max_version: str | None = None
    equals: Any = None
    in_values: list[Any] | None = None
    platforms: list[str] | None = None
    description: str = ""

    @model_validator(mode="after")
    def _validate_constraint_fields(self) -> CapabilityConstraint:
        if self.min_version is not None:
            parse_semver(self.min_version)
        if self.max_version is not None:
            parse_semver(self.max_version)
        if self.min_version and self.max_version:
            if parse_semver(self.min_version) > parse_semver(self.max_version):
                raise ValueError(
                    f"Constraint {self.id!r}: min_version ({self.min_version}) "
                    f"> max_version ({self.max_version})"
                )
        if self.platforms is not None:
            invalid = [p for p in self.platforms if p.lower() not in SUPPORTED_PLATFORMS]
            if invalid:
                raise ValueError(f"Unsupported platforms in constraint {self.id!r}: {invalid}")
            self.platforms = [p.lower() for p in self.platforms]
        return self


class FeatureRule(BaseModel):
    """Compatibility requirements attached to a single Flagsmith feature."""

    model_config = ConfigDict(extra="forbid")

    feature_name: str = Field(..., min_length=1)
    require_enabled: bool = False
    platforms: list[str] | None = None
    disallow_other_platforms: bool = False
    constraints: list[CapabilityConstraint] = Field(default_factory=list)

    @field_validator("platforms")
    @classmethod
    def _validate_platforms(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [p.strip().lower() for p in value]
        invalid = [p for p in normalized if p not in SUPPORTED_PLATFORMS]
        if invalid:
            raise ValueError(f"Unsupported platforms in feature rule: {invalid}")
        return normalized


class RuleSet(BaseModel):
    """Collection of versioned feature compatibility rules."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    rules: list[FeatureRule] = Field(..., min_length=1)

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        if value not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"Unsupported rules schema_version {value!r}; "
                f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )
        return value


class EvaluationFinding(BaseModel):
    """Detailed outcome of evaluating one rule/constraint for a profile + identity."""

    status: EvaluationStatus
    feature_name: str
    identity: str
    profile_id: str
    rule_id: str
    expected_requirement: str
    observed_capability: str
    explanation: str
    source: Literal["flagsmith", "hypothetical"] = "flagsmith"


class ValidationReport(BaseModel):
    """Aggregated compatibility report across evaluated profiles and identities."""

    run_id: str
    environment: str
    strict: bool = False
    total_checks: int
    passed: int
    conflicts: int
    unknowns: int
    skipped: int
    blocking: bool
    findings: list[EvaluationFinding] = Field(default_factory=list)
