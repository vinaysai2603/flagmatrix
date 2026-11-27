"""Phase 5 tests for FastAPI adapter endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from flagmatrix_api.app import app, state
from flagmatrix_core import (
    ApplicationProfile,
    CapabilityConstraint,
    FeatureRule,
    FlagValueState,
    FlagsmithEnvironment,
    FlagsmithProject,
    RuleSet,
)

client = TestClient(app)


def test_api_health_profiles_rules_validation_and_report() -> None:
    state.profiles = [
        ApplicationProfile(
            app_id="com.novapay.wallet",
            tenant_id="novapay",
            platform="android",
            app_version="3.0.0",
            environment="Development",
            sdk_versions={"stripe_sdk": "2.0.0"},
        )
    ]
    state.ruleset = RuleSet(
        rules=[
            FeatureRule(
                feature_name="instant_payouts",
                constraints=[
                    CapabilityConstraint(
                        id="stripe-v3",
                        type="sdk_version",
                        target="stripe_sdk",
                        min_version="3.0.0",
                    )
                ],
            )
        ]
    )

    with patch(
        "flagmatrix_core.flagsmith_client.FlagsmithClient.check_health",
        return_value={"image_tag": "2.295.2", "experimentation_enabled": True},
    ):
        health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["flagsmith"]["connected"] is True

    assert client.get("/api/v1/profiles").status_code == 200
    assert client.get("/api/v1/rules").status_code == 200

    fake_projects = [FlagsmithProject(id=1, name="flagmatrix", organisation=1)]
    fake_envs = [
        FlagsmithEnvironment(id=1, name="Development", api_key="k_dev", project=1),
        FlagsmithEnvironment(id=2, name="Production", api_key="k_prod", project=1),
    ]
    with (
        patch("flagmatrix_core.flagsmith_client.FlagsmithClient.list_projects", return_value=fake_projects),
        patch("flagmatrix_core.flagsmith_client.FlagsmithClient.list_environments", return_value=fake_envs),
        patch(
            "flagmatrix_core.flagsmith_client.FlagsmithClient.get_identity_flags",
            return_value={
                "instant_payouts": FlagValueState(
                    feature_name="instant_payouts", enabled=True, identity="id1"
                )
            },
        ),
    ):
        assert client.get("/api/v1/projects").status_code == 200
        assert client.get("/api/v1/environments?project_id=1").status_code == 200

        run_resp = client.post(
            "/api/v1/validation/run",
            json={"project_id": 1, "environment": "Development", "strict": False},
        )
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        run_id = run_data["run_id"]
        assert run_data["report"]["conflicts"] == 1

        cmp_resp = client.post(
            "/api/v1/environments/compare",
            json={
                "project_id": 1,
                "source_environment": "Development",
                "target_environment": "Production",
            },
        )
        assert cmp_resp.status_code == 200

    assert client.get(f"/api/v1/validation/{run_id}").status_code == 200
    md = client.get(f"/api/v1/reports/{run_id}?format=markdown")
    assert md.status_code == 200
    assert "FlagMatrix Report" in md.text
