"""Centralized identity and trait construction for Flagsmith evaluations."""

from __future__ import annotations

import uuid
from typing import Any

from flagmatrix_core.models import ApplicationProfile


def build_identity_and_traits(
    profile: ApplicationProfile,
    ephemeral: bool = False,
    run_tag: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Construct a deterministic (or isolated transient) Flagsmith identity and traits."""
    base_id = f"{profile.tenant_id}_{profile.platform}_{profile.app_version}"
    if ephemeral:
        suffix = run_tag or uuid.uuid4().hex[:8]
        identifier = f"fm_eval_{base_id}_{suffix}"
    else:
        identifier = base_id

    traits: dict[str, Any] = {
        "tenant_id": profile.tenant_id,
        "app_id": profile.app_id,
        "platform": profile.platform,
        "app_version": profile.app_version,
        "build_flavor": profile.build_flavor,
        **profile.identity_traits,
    }
    return identifier, traits
