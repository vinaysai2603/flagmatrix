"""Phase 2 tests for manifest schemas, semver, and compatibility engine."""

from pathlib import Path

import pytest

from flagmatrix_core import (
    ApplicationProfile,
    CapabilityConstraint,
    CompatibilityEngine,
    EvaluationStatus,
    FeatureRule,
    FlagValueState,
    MalformedVersionError,
    ManifestValidationError,
    RuleSet,
    load_profile,
    load_ruleset,
    parse_semver,
)


def _sample_profile(**overrides) -> ApplicationProfile:
    base = {
        "schema_version": "1.0",
        "app_id": "com.novapay.wallet",
        "tenant_id": "novapay",
        "platform": "android",
        "app_version": "3.4.0",
        "build_flavor": "production",
        "environment": "Production",
        "installed_sdks": ["stripe_sdk", "biometric_auth"],
        "sdk_versions": {"stripe_sdk": "2.1.0", "biometric_auth": "1.5.0"},
        "native_resources": {"launcher_icons": ["ic_launcher", "ic_republic"]},
        "backend_api_versions": {"payments": "2.0.0", "ledger": "1.10.0"},
        "device_capabilities": {"biometrics": True, "nfc": True},
    }
    base.update(overrides)
    return ApplicationProfile(**base)


def test_semver_ordering_and_validation() -> None:
    assert parse_semver("1.10.0") > parse_semver("1.2.0")
    assert parse_semver("v2.0.0") == parse_semver("2.0.0")
    with pytest.raises(MalformedVersionError):
        parse_semver("not-a-version")


def test_manifest_loader_rejects_malformed_and_unknown_fields(tmp_path: Path) -> None:
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        "schema_version: '9.9'\napp_id: app\ntenant_id: t\nplatform: android\n"
        "app_version: '1.0.0'\nenvironment: dev\nextra_field: oops\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestValidationError) as exc_info:
        load_profile(bad_yaml)
    assert "schema_version" in str(exc_info.value)


def test_ruleset_loader_rejects_min_gt_max(tmp_path: Path) -> None:
    bad_rules = tmp_path / "rules.yaml"
    bad_rules.write_text(
        "schema_version: '1.0'\nrules:\n  - feature_name: f1\n    constraints:\n"
        "      - id: c1\n        type: sdk_version\n        target: stripe_sdk\n"
        "        min_version: '3.0.0'\n        max_version: '2.0.0'\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestValidationError):
        load_ruleset(bad_rules)


def test_disabled_feature_is_skipped_unless_required() -> None:
    engine = CompatibilityEngine()
    profile = _sample_profile(sdk_versions={})
    ruleset = RuleSet(
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
    flags = {"instant_payouts": FlagValueState(feature_name="instant_payouts", enabled=False)}
    report = engine.run_validation([(profile, "user_1", flags)], ruleset, "Production")
    assert report.skipped == 1
    assert report.conflicts == 0
    assert report.blocking is False

    ruleset_req = RuleSet(
        rules=[FeatureRule(feature_name="instant_payouts", require_enabled=True)]
    )
    report_req = engine.run_validation([(profile, "user_1", flags)], ruleset_req, "Production")
    assert report_req.conflicts == 1
    assert report_req.blocking is True


def test_missing_capability_is_unknown_and_strict_blocks() -> None:
    engine = CompatibilityEngine()
    profile = _sample_profile(installed_sdks=[], sdk_versions={}, device_capabilities={})
    ruleset = RuleSet(
        rules=[
            FeatureRule(
                feature_name="biometric_login",
                constraints=[
                    CapabilityConstraint(
                        id="bio-sdk", type="sdk_installed", target="biometric_auth"
                    )
                ],
            )
        ]
    )
    flags = {"biometric_login": FlagValueState(feature_name="biometric_login", enabled=True)}

    non_strict = engine.run_validation([(profile, "u1", flags)], ruleset, "Dev", strict=False)
    assert non_strict.unknowns == 1
    assert non_strict.blocking is False

    strict = engine.run_validation([(profile, "u1", flags)], ruleset, "Dev", strict=True)
    assert strict.unknowns == 1
    assert strict.blocking is True


def test_conflicts_for_sdk_icon_backend_and_incompatible_flags() -> None:
    engine = CompatibilityEngine()
    profile = _sample_profile()
    ruleset = RuleSet(
        rules=[
            FeatureRule(
                feature_name="instant_payouts",
                constraints=[
                    CapabilityConstraint(
                        id="stripe-min-3",
                        type="sdk_version",
                        target="stripe_sdk",
                        min_version="3.0.0",
                    ),
                    CapabilityConstraint(
                        id="payments-api-3",
                        type="backend_api_version",
                        target="payments",
                        min_version="3.0.0",
                    ),
                ],
            ),
            FeatureRule(
                feature_name="festival_icon",
                constraints=[
                    CapabilityConstraint(
                        id="diwali-icon",
                        type="native_resource",
                        target="launcher_icons",
                        equals="ic_diwali",
                    )
                ],
            ),
            FeatureRule(
                feature_name="legacy_checkout",
                constraints=[
                    CapabilityConstraint(
                        id="no-v2-checkout",
                        type="incompatible_with",
                        target="v2_checkout",
                    )
                ],
            ),
        ]
    )
    flags = {
        "instant_payouts": FlagValueState(feature_name="instant_payouts", enabled=True),
        "festival_icon": FlagValueState(feature_name="festival_icon", enabled=True),
        "legacy_checkout": FlagValueState(feature_name="legacy_checkout", enabled=True),
        "v2_checkout": FlagValueState(feature_name="v2_checkout", enabled=True),
    }
    report = engine.run_validation([(profile, "tenant_user", flags)], ruleset, "Production")
    assert report.conflicts == 4
    assert report.blocking is True
    for finding in report.findings:
        assert finding.status == EvaluationStatus.CONFLICT
        assert finding.identity == "tenant_user"
        assert finding.profile_id == profile.profile_id
        assert finding.rule_id
        assert finding.expected_requirement
        assert finding.observed_capability
        assert finding.explanation
