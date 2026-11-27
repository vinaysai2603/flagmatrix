"""Phase 3 tests for Flagsmith integration, secret redaction, and testing engine."""

from pathlib import Path

import pytest

from flagmatrix_core import (
    ApplicationProfile,
    CapabilityConstraint,
    ConfigurationTestingEngine,
    FeatureRule,
    FlagsmithClient,
    RuleSet,
    generate_pairwise_flag_configs,
    redact_secret,
)


def _load_local_env() -> tuple[str, str] | None:
    env_file = Path(__file__).resolve().parent.parent / "flagsmith" / "flagsmith.env"
    if not env_file.exists():
        return None
    url = "http://localhost:8000"
    key = ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("export FLAGSMITH_API_URL="):
            url = line.split("=", 1)[1].strip()
        elif line.startswith("export FLAGSMITH_API_KEY_localhost_8000="):
            key = line.split("=", 1)[1].strip()
    if not key:
        return None
    return url, key


def test_redact_secret() -> None:
    assert redact_secret("CI1CYq6r.bZbYDoQRUhQFFUZXcWkZMCAtCw0xU3OU") == "CI1C...U3OU"
    assert redact_secret("short") == "***"
    assert redact_secret("") == "<empty>"


def test_pairwise_generation_and_coverage_separation() -> None:
    domains = {
        "flag_a": [(True, None), (False, None)],
        "flag_b": [(True, None), (False, None)],
        "flag_c": [(True, None), (False, None)],
    }
    configs, covered, total = generate_pairwise_flag_configs(
        domains, forbidden_pairs=[("flag_a", True, "flag_b", True)]
    )
    assert covered == total
    assert len(configs) < 8  # pairwise is smaller than full 2^3=8

    profile = ApplicationProfile(
        app_id="com.example.app",
        tenant_id="novapay",
        platform="android",
        app_version="1.0.0",
        environment="Development",
    )
    ruleset = RuleSet(
        rules=[
            FeatureRule(
                feature_name="flag_a",
                constraints=[
                    CapabilityConstraint(
                        id="no-b", type="incompatible_with", target="flag_b"
                    )
                ],
            )
        ]
    )
    hypo_cases = [(profile, f"hypo-{i}", cfg) for i, cfg in enumerate(configs)]
    engine = ConfigurationTestingEngine()
    res = engine.run_suite(
        flagsmith_cases=[],
        ruleset=ruleset,
        environment="Development",
        hypothetical_cases=hypo_cases,
        pairwise_features=list(domains.keys()),
        covered_pairs=covered,
        total_pairs=total,
    )
    assert res.coverage.flagsmith_cases == 0
    assert res.coverage.hypothetical_cases == len(configs)
    assert res.coverage.achieved_pairwise_coverage == 100.0
    assert res.coverage.exhaustive is False


@pytest.mark.live
def test_live_local_flagsmith_integration() -> None:
    creds = _load_local_env()
    assert creds is not None, "flagsmith/flagsmith.env must exist for local integration test"
    url, key = creds
    client = FlagsmithClient(base_url=url, api_key=key)

    version = client.check_health()
    assert version["experimentation_enabled"] is True

    projects = client.list_projects()
    assert len(projects) >= 1
    project = projects[0]

    envs = client.list_environments(project.id)
    env_names = {e.name for e in envs}
    assert {"Development", "Production"}.issubset(env_names)

    dev_env = next(e for e in envs if e.name == "Development")
    env_flags = client.get_environment_flags(dev_env.api_key)
    id_flags = client.get_identity_flags(
        dev_env.api_key,
        identifier="sandbox_test_identity",
        traits={"tenant": "novapay", "platform": "android"},
    )
    assert isinstance(env_flags, dict)
    assert isinstance(id_flags, dict)
