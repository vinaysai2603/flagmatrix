"""Phase 7 end-to-end tests for fintech scenarios, boundary cases, and pairwise coverage."""

from pathlib import Path

from flagmatrix_core import (
    CompatibilityEngine,
    EvaluationStatus,
    FlagValueState,
    load_profiles,
    load_ruleset,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_fintech_examples_load_and_detect_exact_conflicts() -> None:
    profiles = {p.tenant_id: p for p in load_profiles(EXAMPLES_DIR / "profiles")}
    ruleset = load_ruleset(EXAMPLES_DIR / "rules.yaml")
    assert set(profiles.keys()) == {"novapay", "aurelia", "kinetix"}

    engine = CompatibilityEngine()

    # NovaPay Android: incompatible stripe_sdk (2.1.0), payments API (1.9.0), missing ic_diwali, legacy+biometric conflict
    novapay_flags = {
        "instant_payouts": FlagValueState(feature_name="instant_payouts", enabled=True, identity="novapay_id"),
        "biometric_checkout": FlagValueState(feature_name="biometric_checkout", enabled=True, identity="novapay_id"),
        "festival_launcher_icon": FlagValueState(feature_name="festival_launcher_icon", enabled=True, identity="novapay_id"),
        "legacy_pin_flow": FlagValueState(feature_name="legacy_pin_flow", enabled=True, identity="novapay_id"),
    }
    # Aurelia iOS: fully compatible
    aurelia_flags = {
        "instant_payouts": FlagValueState(feature_name="instant_payouts", enabled=True, identity="aurelia_id"),
        "biometric_checkout": FlagValueState(feature_name="biometric_checkout", enabled=True, identity="aurelia_id"),
        "festival_launcher_icon": FlagValueState(feature_name="festival_launcher_icon", enabled=True, identity="aurelia_id"),
        "legacy_pin_flow": FlagValueState(feature_name="legacy_pin_flow", enabled=False, identity="aurelia_id"),
    }
    # Kinetix Web: biometric_checkout enabled on web -> platform conflict; festival_launcher_icon -> skipped
    kinetix_flags = {
        "instant_payouts": FlagValueState(feature_name="instant_payouts", enabled=True, identity="kinetix_id"),
        "biometric_checkout": FlagValueState(feature_name="biometric_checkout", enabled=True, identity="kinetix_id"),
        "festival_launcher_icon": FlagValueState(feature_name="festival_launcher_icon", enabled=True, identity="kinetix_id"),
        "legacy_pin_flow": FlagValueState(feature_name="legacy_pin_flow", enabled=False, identity="kinetix_id"),
    }

    report = engine.run_validation(
        [
            (profiles["novapay"], "novapay_id", novapay_flags),
            (profiles["aurelia"], "aurelia_id", aurelia_flags),
            (profiles["kinetix"], "kinetix_id", kinetix_flags),
        ],
        ruleset,
        environment="Production",
    )

    conflict_rules = {
        (f.identity, f.rule_id)
        for f in report.findings
        if f.status == EvaluationStatus.CONFLICT
    }
    assert ("novapay_id", "stripe-sdk-min-v3") in conflict_rules
    assert ("novapay_id", "payments-api-min-v2") in conflict_rules
    assert ("novapay_id", "diwali-launcher-icon-present") in conflict_rules
    assert ("novapay_id", "legacy-pin-conflicts-biometric") in conflict_rules
    assert ("kinetix_id", "biometric_checkout:platform-support") in conflict_rules
    assert not any(ident == "aurelia_id" for ident, _ in conflict_rules)
    assert report.blocking is True


def test_fixed_novapay_passes_release_gate() -> None:
    profiles = {p.tenant_id: p for p in load_profiles(EXAMPLES_DIR / "profiles")}
    ruleset = load_ruleset(EXAMPLES_DIR / "rules.yaml")

    fixed_novapay = profiles["novapay"].model_copy(
        update={
            "sdk_versions": {"stripe_sdk": "3.0.0", "biometric_auth": "1.4.0"},
            "backend_api_versions": {"payments": "2.0.0"},
            "native_resources": {"launcher_icons": ["ic_launcher", "ic_diwali"]},
        }
    )
    flags = {
        "instant_payouts": FlagValueState(feature_name="instant_payouts", enabled=True, identity="novapay_id"),
        "biometric_checkout": FlagValueState(feature_name="biometric_checkout", enabled=True, identity="novapay_id"),
        "festival_launcher_icon": FlagValueState(feature_name="festival_launcher_icon", enabled=True, identity="novapay_id"),
        "legacy_pin_flow": FlagValueState(feature_name="legacy_pin_flow", enabled=False, identity="novapay_id"),
    }
    report = CompatibilityEngine().run_validation(
        [(fixed_novapay, "novapay_id", flags)],
        ruleset,
        environment="Production",
        strict=True,
    )
    assert report.conflicts == 0
    assert report.unknowns == 0
    assert report.blocking is False
