"""Semantic version parsing and SemVer 2.0.0 comparison utilities."""

from __future__ import annotations

import re

from semver import Version


class MalformedVersionError(ValueError):
    """Raised when a version string cannot be parsed as a valid semantic version."""


_TWO_PART_RE = re.compile(r"^(\d+\.\d+)([-+].*)?$")


def parse_semver(raw: str) -> Version:
    """Parse a SemVer 2.0.0 string (supporting optional leading 'v' and X.Y shorthand)."""
    if not isinstance(raw, str):
        raise MalformedVersionError(f"Expected version string, got {type(raw).__name__}")
    cleaned = raw.strip()
    if cleaned.startswith("v") and len(cleaned) > 1 and cleaned[1].isdigit():
        cleaned = cleaned[1:]
    match = _TWO_PART_RE.match(cleaned)
    if match:
        cleaned = f"{match.group(1)}.0{match.group(2) or ''}"
    try:
        return Version.parse(cleaned)
    except ValueError as exc:
        raise MalformedVersionError(f"Invalid semantic version: {raw!r}") from exc


def compare_semver(left: str, right: str) -> int:
    """Compare two SemVer 2.0.0 strings, ignoring build metadata per spec.

    Returns -1 if left < right, 0 if equal precedence, 1 if left > right.
    """
    return parse_semver(left).compare(parse_semver(right))


def satisfies_version_range(
    observed: str,
    min_version: str | None = None,
    max_version: str | None = None,
) -> tuple[bool, str]:
    """Check whether an observed version satisfies optional min/max bounds."""
    obs = parse_semver(observed)
    if min_version is not None:
        min_v = parse_semver(min_version)
        if obs.compare(min_v) < 0:
            return False, f"observed {observed} < required minimum {min_version}"
    if max_version is not None:
        max_v = parse_semver(max_version)
        if obs.compare(max_v) > 0:
            return False, f"observed {observed} > allowed maximum {max_version}"
    return True, f"observed {observed} satisfies version bounds"
