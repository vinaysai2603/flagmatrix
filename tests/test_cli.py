"""Phase 4 tests for FlagMatrix CLI commands and exit codes."""

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from flagmatrix_cli.main import EXIT_CONFLICT, EXIT_ERROR, EXIT_OK, app
from flagmatrix_core import FlagValueState, FlagsmithEnvironment, FlagsmithProject

runner = CliRunner()


def test_cli_init_and_report(tmp_path: Path) -> None:
    res = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert res.exit_code == 0
    assert (tmp_path / "flagmatrix.yaml").exists()
    assert (tmp_path / "rules.yaml").exists()
    assert (tmp_path / "profiles" / "sample_android.yaml").exists()


def test_cli_validate_exit_codes_and_json_report(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    report_file = tmp_path / "report.json"

    fake_projects = [FlagsmithProject(id=1, name="flagmatrix", organisation=1)]
    fake_envs = [
        FlagsmithEnvironment(id=1, name="Development", api_key="env_dev", project=1),
        FlagsmithEnvironment(id=2, name="Production", api_key="env_prod", project=1),
    ]

    # Case 1: PASS (exit 0)
    with (
        patch("flagmatrix_cli.main.FlagsmithClient.list_environments", return_value=fake_envs),
        patch(
            "flagmatrix_cli.main.FlagsmithClient.get_identity_flags",
            return_value={
                "instant_payouts": FlagValueState(
                    feature_name="instant_payouts", enabled=True, identity="id1"
                )
            },
        ),
    ):
        res_ok = runner.invoke(
            app,
            [
                "validate",
                "--config",
                str(tmp_path / "flagmatrix.yaml"),
                "--profiles",
                str(tmp_path / "profiles"),
                "--rules",
                str(tmp_path / "rules.yaml"),
                "--api-key",
                "test_key",
                "--json",
                "--report-out",
                str(report_file),
            ],
        )
    assert res_ok.exit_code == EXIT_OK
    assert report_file.exists()
    data = json.loads(report_file.read_text(encoding="utf-8"))
    assert data["passed"] == 1
    assert data["blocking"] is False

    # Case 2: report command renders markdown
    res_rep = runner.invoke(app, ["report", str(report_file), "--format", "markdown"])
    assert res_rep.exit_code == 0
    assert "FlagMatrix Report" in res_rep.stdout

    # Case 3: CONFLICT (exit 1) when stripe_sdk is too old
    (tmp_path / "profiles" / "sample_android.yaml").write_text(
        'schema_version: "1.0"\n'
        "app_id: com.example.fintech\n"
        "tenant_id: sample_tenant\n"
        "platform: android\n"
        'app_version: "1.0.0"\n'
        "environment: Development\n"
        "sdk_versions:\n"
        '  stripe_sdk: "2.0.0"\n',
        encoding="utf-8",
    )
    with (
        patch("flagmatrix_cli.main.FlagsmithClient.list_environments", return_value=fake_envs),
        patch(
            "flagmatrix_cli.main.FlagsmithClient.get_identity_flags",
            return_value={
                "instant_payouts": FlagValueState(
                    feature_name="instant_payouts", enabled=True, identity="id1"
                )
            },
        ),
    ):
        res_conflict = runner.invoke(
            app,
            [
                "validate",
                "--profiles",
                str(tmp_path / "profiles"),
                "--rules",
                str(tmp_path / "rules.yaml"),
                "--api-key",
                "test_key",
            ],
        )
    assert res_conflict.exit_code == EXIT_CONFLICT

    # Case 4: Invalid manifest (exit 2)
    (tmp_path / "profiles" / "sample_android.yaml").write_text("bad: [", encoding="utf-8")
    res_err = runner.invoke(
        app,
        [
            "validate",
            "--profiles",
            str(tmp_path / "profiles"),
            "--rules",
            str(tmp_path / "rules.yaml"),
            "--api-key",
            "test_key",
        ],
    )
    assert res_err.exit_code == EXIT_ERROR

    # Case 5: connect command redacts key and omits environment api_key
    with (
        patch("flagmatrix_cli.main.FlagsmithClient.check_health", return_value={"image_tag": "2.295.2", "experimentation_enabled": True}),
        patch("flagmatrix_cli.main.FlagsmithClient.list_projects", return_value=fake_projects),
        patch("flagmatrix_cli.main.FlagsmithClient.list_environments", return_value=fake_envs),
    ):
        res_conn = runner.invoke(app, ["connect", "--api-key", "test_synthetic_key_0001", "--json"])
    assert res_conn.exit_code == EXIT_OK
    assert "test_synthetic_key_0001" not in res_conn.stdout
    assert "test...0001" in res_conn.stdout
    assert "env_dev" not in res_conn.stdout
