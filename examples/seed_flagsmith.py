"""Idempotent seed script for an isolated FlagMatrix Demo project in self-hosted Flagsmith.

Usage:
    Set FLAGSMITH_API_URL and FLAGSMITH_API_KEY (or FLAGSMITH_API_KEY_localhost_8000), then:
    python examples/seed_flagsmith.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

_CORE_DIR = Path(__file__).resolve().parents[1] / "core"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from flagmatrix_core import redact_secret  # noqa: E402

FEATURES = [
    ("instant_payouts", False),
    ("biometric_checkout", False),
    ("festival_launcher_icon", False),
    ("legacy_pin_flow", False),
]

TENANT_OVERRIDES: dict[str, tuple[int, dict[str, bool]]] = {
    "novapay": (
        1,
        {
            "instant_payouts": True,
            "biometric_checkout": True,
            "festival_launcher_icon": True,
            "legacy_pin_flow": True,
        },
    ),
    "aurelia": (
        2,
        {
            "instant_payouts": True,
            "biometric_checkout": True,
            "festival_launcher_icon": True,
            "legacy_pin_flow": False,
        },
    ),
    "kinetix": (
        3,
        {
            "instant_payouts": True,
            "biometric_checkout": True,
            "festival_launcher_icon": False,
            "legacy_pin_flow": False,
        },
    ),
}


def _resolve_auth_header(url: str) -> tuple[dict[str, str], str]:
    parsed = urlparse(url)
    host_key = f"FLAGSMITH_API_KEY_{parsed.netloc.replace(':', '_')}"
    api_key = os.environ.get(host_key) or os.environ.get("FLAGSMITH_API_KEY")
    if api_key:
        return {"Authorization": f"Api-Key {api_key}"}, redact_secret(api_key)
    token = os.environ.get("FLAGSMITH_AUTH_TOKEN")
    if token:
        return {"Authorization": f"Token {token}"}, redact_secret(token)
    raise RuntimeError(
        f"Missing Flagsmith credentials. Set {host_key}, FLAGSMITH_API_KEY, or FLAGSMITH_AUTH_TOKEN."
    )


def _extract_items(data: object) -> list[dict]:
    if isinstance(data, dict):
        return list(data.get("results", []))
    if isinstance(data, list):
        return data
    return []


def _get_or_create_project(client: httpx.Client, org_id: int, name: str) -> dict:
    resp = client.get("/api/v1/projects/")
    resp.raise_for_status()
    items = _extract_items(resp.json())
    for proj in items:
        if proj["name"] == name:
            return proj
    created = client.post("/api/v1/projects/", json={"name": name, "organisation": org_id})
    if created.status_code == 403 and items:
        print(
            f"Note: Creating a new project returned 403; reusing existing project "
            f"'{items[0]['name']}' (id={items[0]['id']})."
        )
        return items[0]
    created.raise_for_status()
    return created.json()


def _get_or_create_env(client: httpx.Client, project_id: int, name: str) -> dict:
    resp = client.get(f"/api/v1/environments/?project={project_id}")
    resp.raise_for_status()
    for env in _extract_items(resp.json()):
        if env["name"] == name:
            return env
    created = client.post("/api/v1/environments/", json={"name": name, "project": project_id})
    created.raise_for_status()
    return created.json()


def _get_or_create_feature(
    client: httpx.Client, project_id: int, name: str, default_enabled: bool
) -> dict:
    resp = client.get(f"/api/v1/projects/{project_id}/features/")
    resp.raise_for_status()
    for feat in _extract_items(resp.json()):
        if feat["name"] == name:
            return feat
    created = client.post(
        f"/api/v1/projects/{project_id}/features/",
        json={
            "name": name,
            "type": "STANDARD",
            "default_enabled": default_enabled,
        },
    )
    created.raise_for_status()
    return created.json()


def _get_or_create_segment(
    client: httpx.Client, project_id: int, name: str, tenant_id: str
) -> dict:
    resp = client.get(f"/api/v1/projects/{project_id}/segments/")
    resp.raise_for_status()
    for seg in _extract_items(resp.json()):
        if seg["name"] == name:
            return seg
    payload = {
        "name": name,
        "project": project_id,
        "rules": [
            {
                "type": "ALL",
                "rules": [],
                "conditions": [
                    {
                        "operator": "EQUAL",
                        "property": "tenant_id",
                        "value": tenant_id,
                    }
                ],
            }
        ],
    }
    created = client.post(f"/api/v1/projects/{project_id}/segments/", json=payload)
    created.raise_for_status()
    return created.json()


def _upsert_segment_override(
    client: httpx.Client,
    env_id: int,
    env_api_key: str,
    feature_id: int,
    segment_id: int,
    enabled: bool,
    priority: int,
) -> None:
    seg_links_resp = client.get(
        f"/api/v1/features/feature-segments/?environment={env_id}&feature={feature_id}"
    )
    seg_links_resp.raise_for_status()
    seg_links = _extract_items(seg_links_resp.json())

    seg_link = next((s for s in seg_links if s.get("segment") == segment_id), None)
    if seg_link is None:
        fs_resp = client.post(
            "/api/v1/features/feature-segments/",
            json={
                "feature": feature_id,
                "segment": segment_id,
                "environment": env_id,
                "priority": priority,
            },
        )
        fs_resp.raise_for_status()
        seg_link = fs_resp.json()

    seg_link_id = seg_link["id"]
    states_resp = client.get(
        f"/api/v1/features/featurestates/?environment={env_id}&feature={feature_id}"
    )
    states_resp.raise_for_status()
    states = _extract_items(states_resp.json())

    existing_state = next(
        (fs for fs in states if fs.get("feature_segment") == seg_link_id),
        None,
    )
    if existing_state is not None:
        if existing_state.get("enabled") != enabled:
            patch = client.patch(
                f"/api/v1/features/featurestates/{existing_state['id']}/",
                json={"enabled": enabled},
            )
            patch.raise_for_status()
        return

    create_fs = client.post(
        "/api/v1/features/featurestates/",
        json={
            "feature": feature_id,
            "environment": env_id,
            "feature_segment": seg_link_id,
            "enabled": enabled,
        },
    )
    create_fs.raise_for_status()


def seed() -> None:
    base_url = os.environ.get("FLAGSMITH_API_URL", "http://localhost:8000").rstrip("/")
    headers, redacted_key = _resolve_auth_header(base_url)
    project_name = os.environ.get("FLAGMATRIX_DEMO_PROJECT", "FlagMatrix Demo")

    print(f"Seeding Flagsmith at {base_url} (credential={redacted_key})...")

    with httpx.Client(base_url=base_url, headers=headers, timeout=15.0) as client:
        orgs_resp = client.get("/api/v1/organisations/")
        orgs_resp.raise_for_status()
        orgs = _extract_items(orgs_resp.json())
        if not orgs:
            raise RuntimeError("No organisations found in Flagsmith.")
        org_id = orgs[0]["id"]

        project = _get_or_create_project(client, org_id, project_name)
        project_id = project["id"]
        actual_project_name = project["name"]
        dev_env = _get_or_create_env(client, project_id, "Development")
        prod_env = _get_or_create_env(client, project_id, "Production")

        feature_map = {
            name: _get_or_create_feature(client, project_id, name, default_en)
            for name, default_en in FEATURES
        }

        segment_map = {
            tenant: _get_or_create_segment(client, project_id, f"{tenant}_tenant", tenant)
            for tenant in TENANT_OVERRIDES
        }

        for env in (dev_env, prod_env):
            eid = env["id"]
            ekey = env["api_key"]
            for tenant, (priority, flag_states) in TENANT_OVERRIDES.items():
                seg_id = segment_map[tenant]["id"]
                for feat_name, enabled in flag_states.items():
                    _upsert_segment_override(
                        client,
                        eid,
                        ekey,
                        feature_map[feat_name]["id"],
                        seg_id,
                        enabled,
                        priority,
                    )

    print(
        f"Seeded project '{actual_project_name}' (id={project_id}) with Development/Production, "
        f"{len(feature_map)} features, and {len(segment_map)} tenant segments."
    )


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
