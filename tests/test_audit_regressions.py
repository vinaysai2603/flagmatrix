"""Regression tests for Phase 1 correctness and Phase 3 security/precedence audit items."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from typer.testing import CliRunner

from flagmatrix_api.app import app as api_app
from flagmatrix_api.state import AppState
from flagmatrix_cli.config import load_config
from flagmatrix_cli.main import EXIT_ERROR, EXIT_OK, app as cli_app
from flagmatrix_core import (
    ApplicationProfile,
    CapabilityConstraint,
    CompatibilityEngine,
    FeatureRule,
    FlagValueState,
    FlagsmithClient,
    FlagsmithConnectionError,
    FlagsmithEnvironment,
    RuleSet,
    build_identity_and_traits,
    compare_environments,
    compare_semver,
    satisfies_version_range,
)


def _profile(tenant: str, platform: str = "android", stripe: str = "3.0.0") -> ApplicationProfile:
    return ApplicationProfile(
        app_id=f"com.{tenant}.app",
        tenant_id=tenant,
        platform=platform,
        app_version="1.0.0",
        environment="Production",
        sdk_versions={"stripe_sdk": stripe},
    )


def test_compare_evaluates_all_profiles_and_individual_finding_keys() -> None:
    p1 = _profile("novapay", stripe="2.0.0")
    p2 = _profile("aurelia", stripe="2.0.0")
    ruleset = RuleSet(
        rules=[
            FeatureRule(
                feature_name="f1",
                constraints=[
                    CapabilityConstraint(
                        id="c1", type="sdk_version", target="stripe_sdk", min_version="3.0.0"
                    )
                ],
            ),
            FeatureRule(
                feature_name="f2",
                constraints=[
                    CapabilityConstraint(
                        id="c2", type="sdk_version", target="stripe_sdk", min_version="3.0.0"
                    )
                ],
            ),
        ]
    )

    # Source: p1 fails f1; p2 passes (disabled f2)
    src_evals = [
        (p1, "id1", {"f1": FlagValueState(feature_name="f1", enabled=True), "f2": FlagValueState(feature_name="f2", enabled=False)}),
        (p2, "id2", {"f1": FlagValueState(feature_name="f1", enabled=False), "f2": FlagValueState(feature_name="f2", enabled=False)}),
    ]
    # Target: p1 fixes f1, but p2 enables f2 -> 1 conflict fixed, 1 NEW conflict introduced!
    tgt_evals = [
        (p1, "id1", {"f1": FlagValueState(feature_name="f1", enabled=False), "f2": FlagValueState(feature_name="f2", enabled=False)}),
        (p2, "id2", {"f1": FlagValueState(feature_name="f1", enabled=False), "f2": FlagValueState(feature_name="f2", enabled=True)}),
    ]

    cmp = compare_environments("Development", "Production", src_evals, tgt_evals, ruleset)
    assert len(cmp.flag_diffs) == 2
    assert {d.identity for d in cmp.flag_diffs} == {"id1", "id2"}
    assert cmp.new_conflicts_in_target == 1
    assert any("aurelia" in k and "f2|c2" in k for k in cmp.new_conflict_keys)


def test_reject_empty_ruleset_and_empty_evaluations() -> None:
    with pytest.raises(ValidationError):
        RuleSet(schema_version="1.0", rules=[])

    engine = CompatibilityEngine()
    valid_rules = RuleSet(rules=[FeatureRule(feature_name="f1")])
    with pytest.raises(ValueError, match="zero evaluated profiles"):
        engine.run_validation([], valid_rules, "Development")


def test_app_state_surfaces_malformed_default_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad_rules = tmp_path / "examples" / "rules.yaml"
    bad_rules.parent.mkdir(parents=True)
    bad_rules.write_text("schema_version: '1.0'\nrules: []\n", encoding="utf-8")

    # Point state loader to tmp_path via __file__ parent resolution simulation
    state = AppState.__new__(AppState)
    state.flagsmith_url = "http://localhost:8000"
    state.flagsmith_api_key = None
    state.profiles = []
    state.ruleset = None
    state.startup_error = None
    state.history = {}

    from flagmatrix_core import ManifestValidationError, load_ruleset

    with pytest.raises(ManifestValidationError):
        load_ruleset(bad_rules)


def test_semver_prerelease_and_build_metadata() -> None:
    assert compare_semver("1.0.0-alpha", "1.0.0-alpha.1") < 0
    assert compare_semver("1.0.0-alpha.1", "1.0.0-beta") < 0
    assert compare_semver("1.0.0-rc.1", "1.0.0") < 0
    assert compare_semver("1.0.0+build.1", "1.0.0+build.99") == 0

    ok, _ = satisfies_version_range("2.0.0-rc.1+sha123", min_version="2.0.0")
    assert ok is False
    ok_meta, _ = satisfies_version_range("2.0.0+build.5", min_version="2.0.0", max_version="2.0.0")
    assert ok_meta is True


def test_relative_config_paths_resolve_against_config_dir(tmp_path: Path) -> None:
    sub = tmp_path / "nested"
    (sub / "profiles").mkdir(parents=True)
    cfg_file = sub / "flagmatrix.yaml"
    cfg_file.write_text(
        'schema_version: "1.0"\nprofiles_path: profiles\nrules_path: rules.yaml\n',
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert cfg.resolve_path(cfg.profiles_path) == (sub / "profiles").resolve()
    assert cfg.resolve_path(cfg.rules_path) == (sub / "rules.yaml").resolve()


def test_centralized_identity_and_traits() -> None:
    p = _profile("novapay")
    det_id, traits = build_identity_and_traits(p, ephemeral=False)
    eph_id, eph_traits = build_identity_and_traits(p, ephemeral=True, run_tag="ci123")
    assert det_id == "novapay_android_1.0.0"
    assert eph_id == "fm_eval_novapay_android_1.0.0_ci123"
    assert traits == eph_traits
    assert traits["app_version"] == "1.0.0"
    assert traits["tenant_id"] == "novapay"


def test_sdk_failure_returns_documented_exit_code_2(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli_app, ["init", "--dir", str(tmp_path)])
    envs = [FlagsmithEnvironment(id=1, name="Development", api_key="synth_key", project=1)]

    with (
        patch("flagmatrix_cli.main.FlagsmithClient.list_environments", return_value=envs),
        patch.object(
            FlagsmithClient,
            "get_identity_flags",
            side_effect=FlagsmithConnectionError("SDK network failure"),
        ),
    ):
        res = runner.invoke(
            cli_app,
            [
                "validate",
                "--config",
                str(tmp_path / "flagmatrix.yaml"),
                "--api-key",
                "synth_key",
            ],
        )
    assert res.exit_code == EXIT_ERROR


def test_cli_flag_precedence_overrides_config(tmp_path: Path) -> None:
    runner = CliRunner()
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "p.yaml").write_text(
        'schema_version: "1.0"\napp_id: a\ntenant_id: t\nplatform: android\n'
        'app_version: "1.0.0"\nenvironment: Development\n',
        encoding="utf-8",
    )
    (tmp_path / "rules.yaml").write_text(
        'schema_version: "1.0"\nrules:\n  - feature_name: f1\n    constraints:\n'
        "      - id: bio\n        type: sdk_installed\n        target: bio_sdk\n",
        encoding="utf-8",
    )
    (tmp_path / "flagmatrix.yaml").write_text(
        'schema_version: "1.0"\nstrict: true\nenvironment: Development\n',
        encoding="utf-8",
    )
    envs = [FlagsmithEnvironment(id=1, name="Development", api_key="synth_key", project=1)]
    with (
        patch("flagmatrix_cli.main.FlagsmithClient.list_environments", return_value=envs),
        patch(
            "flagmatrix_cli.main.FlagsmithClient.get_identity_flags",
            return_value={"f1": FlagValueState(feature_name="f1", enabled=True)},
        ),
    ):
        # Config has strict: true, but --no-strict overrides it -> UNKNOWN does not block!
        res = runner.invoke(
            cli_app,
            [
                "validate",
                "--config",
                str(tmp_path / "flagmatrix.yaml"),
                "--no-strict",
                "--api-key",
                "synth_key",
            ],
        )
    assert res.exit_code == EXIT_OK


def test_api_security_omits_env_keys_and_blocks_remote_url() -> None:
    client = TestClient(api_app)
    envs = [FlagsmithEnvironment(id=1, name="Development", api_key="synth_secret_env_key", project=1)]
    with patch("flagmatrix_core.flagsmith_client.FlagsmithClient.list_environments", return_value=envs):
        resp = client.get("/api/v1/environments?project_id=1")
    assert resp.status_code == 200
    assert "api_key" not in resp.json()[0]
    assert "synth_secret_env_key" not in resp.text

    bad_conn = client.post("/api/v1/connection", json={"url": "http://169.254.169.254/latest"})
    assert bad_conn.status_code == 400
