"""Semantic version parsing and range comparison utilities."""

from __future__ import annotations

from packaging.version import InvalidVersion, Version


class MalformedVersionError(ValueError):
    """Raised when a version string cannot be parsed as a valid semantic version."""


def parse_semver(raw: str) -> Version:
    """Parse a version string into a packaging.version.Version."""
    cleaned = raw.strip()
    if cleaned.startswith("v") and len(cleaned) > 1 and cleaned[1].isdigit():
        cleaned = cleaned[1:]
    try:
        return Version(cleaned)
    except InvalidVersion as exc:
        raise MalformedVersionError(f"Invalid semantic version: {raw!r}") from exc


def satisfies_version_range(
    observed: str,
    min_version: str | None = None,
    max_version: str | None = None,
) -> tuple[bool, str]:
    """Check whether an observed version satisfies optional min/max bounds."""
    obs = parse_semver(observed)
    if min_version is not None:
        min_v = parse_semver(min_version)
        if obs < min_v:
            return False, f"observed {observed} < required minimum {min_version}"
    if max_version is not None:
        max_v = parse_semver(max_version)
        if obs > max_v:
            return False, f"observed {observed} > allowed maximum {max_version}"
    return True, f"observed {observed} satisfies version bounds"
