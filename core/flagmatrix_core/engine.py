"""Deterministic feature configuration compatibility engine."""

from __future__ import annotations

import uuid
from typing import Any

from flagmatrix_core.models import (
    ApplicationProfile,
    CapabilityConstraint,
    EvaluationFinding,
    EvaluationStatus,
    FeatureRule,
    FlagValueState,
    RuleSet,
    ValidationReport,
)
from flagmatrix_core.semver import MalformedVersionError, satisfies_version_range


def _describe_expected(c: CapabilityConstraint) -> str:
    parts = [f"{c.type}:{c.target}"]
    if c.min_version is not None:
        parts.append(f">={c.min_version}")
    if c.max_version is not None:
        parts.append(f"<={c.max_version}")
    if c.equals is not None:
        parts.append(f"=={c.equals!r}")
    if c.in_values is not None:
        parts.append(f"in {c.in_values!r}")
    return " ".join(parts)


def _check_value_match(observed: Any, c: CapabilityConstraint) -> tuple[bool, str]:
    if c.equals is not None and observed != c.equals:
        return False, f"observed {observed!r} != expected {c.equals!r}"
    if c.in_values is not None:
        if isinstance(observed, (list, tuple, set)):
            if not any(item in observed for item in c.in_values):
                return False, f"none of {c.in_values!r} present in {list(observed)!r}"
        elif observed not in c.in_values:
            return False, f"observed {observed!r} not in {c.in_values!r}"
    if c.min_version is not None or c.max_version is not None:
        if not isinstance(observed, str):
            return False, f"expected semver string, got {type(observed).__name__}"
        try:
            return satisfies_version_range(observed, c.min_version, c.max_version)
        except MalformedVersionError as exc:
            return False, str(exc)
    return True, f"observed {observed!r} matches requirement"


class CompatibilityEngine:
    """Evaluates Flagsmith feature states against declared ApplicationProfiles."""

    def evaluate_profile(
        self,
        profile: ApplicationProfile,
        flags: dict[str, FlagValueState],
        ruleset: RuleSet,
        identity: str,
    ) -> list[EvaluationFinding]:
        """Evaluate every rule in ruleset for a single profile and identity."""
        findings: list[EvaluationFinding] = []
        for rule in ruleset.rules:
            findings.extend(self._evaluate_rule(profile, flags, rule, identity))
        return findings

    def _evaluate_rule(
        self,
        profile: ApplicationProfile,
        flags: dict[str, FlagValueState],
        rule: FeatureRule,
        identity: str,
    ) -> list[EvaluationFinding]:
        flag = flags.get(rule.feature_name)
        source = flag.source if flag is not None else "flagsmith"

        if flag is None:
            status = (
                EvaluationStatus.CONFLICT
                if rule.require_enabled
                else EvaluationStatus.UNKNOWN
            )
            return [
                EvaluationFinding(
                    status=status,
                    feature_name=rule.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=f"{rule.feature_name}:flag-presence",
                    expected_requirement=(
                        "feature present and enabled"
                        if rule.require_enabled
                        else "feature present in Flagsmith environment"
                    ),
                    observed_capability="flag not returned by Flagsmith",
                    explanation=(
                        f"Feature {rule.feature_name!r} was not returned for identity "
                        f"{identity!r}."
                    ),
                    source=source,
                )
            ]

        if not flag.enabled:
            if rule.require_enabled:
                return [
                    EvaluationFinding(
                        status=EvaluationStatus.CONFLICT,
                        feature_name=rule.feature_name,
                        identity=identity,
                        profile_id=profile.profile_id,
                        rule_id=f"{rule.feature_name}:require-enabled",
                        expected_requirement="enabled == True",
                        observed_capability="enabled == False",
                        explanation=(
                            f"Feature {rule.feature_name!r} is disabled for {identity!r}, "
                            f"but rule requires it to be enabled."
                        ),
                        source=source,
                    )
                ]
            return [
                EvaluationFinding(
                    status=EvaluationStatus.SKIPPED,
                    feature_name=rule.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=f"{rule.feature_name}:disabled",
                    expected_requirement="feature enabled before checking constraints",
                    observed_capability="enabled == False",
                    explanation=(
                        f"Feature {rule.feature_name!r} is disabled for {identity!r}; "
                        f"constraints skipped."
                    ),
                    source=source,
                )
            ]

        if rule.platforms is not None and profile.platform not in rule.platforms:
            if rule.disallow_other_platforms:
                return [
                    EvaluationFinding(
                        status=EvaluationStatus.CONFLICT,
                        feature_name=rule.feature_name,
                        identity=identity,
                        profile_id=profile.profile_id,
                        rule_id=f"{rule.feature_name}:platform-support",
                        expected_requirement=f"platform in {rule.platforms!r}",
                        observed_capability=f"platform == {profile.platform!r}",
                        explanation=(
                            f"Feature {rule.feature_name!r} is enabled on unsupported "
                            f"platform {profile.platform!r}."
                        ),
                        source=source,
                    )
                ]
            return [
                EvaluationFinding(
                    status=EvaluationStatus.SKIPPED,
                    feature_name=rule.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=f"{rule.feature_name}:platform-scope",
                    expected_requirement=f"platform in {rule.platforms!r}",
                    observed_capability=f"platform == {profile.platform!r}",
                    explanation=(
                        f"Rule for {rule.feature_name!r} only targets {rule.platforms!r}; "
                        f"skipped for {profile.platform!r}."
                    ),
                    source=source,
                )
            ]

        if not rule.constraints:
            return [
                EvaluationFinding(
                    status=EvaluationStatus.PASS,
                    feature_name=rule.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=f"{rule.feature_name}:enabled",
                    expected_requirement="enabled == True",
                    observed_capability="enabled == True",
                    explanation=f"Feature {rule.feature_name!r} is enabled with no extra constraints.",
                    source=source,
                )
            ]

        results: list[EvaluationFinding] = []
        for constraint in rule.constraints:
            if constraint.platforms is not None and profile.platform not in constraint.platforms:
                results.append(
                    EvaluationFinding(
                        status=EvaluationStatus.SKIPPED,
                        feature_name=rule.feature_name,
                        identity=identity,
                        profile_id=profile.profile_id,
                        rule_id=constraint.id,
                        expected_requirement=_describe_expected(constraint),
                        observed_capability=f"platform == {profile.platform!r}",
                        explanation=(
                            f"Constraint {constraint.id!r} applies only to "
                            f"{constraint.platforms!r}; skipped for {profile.platform!r}."
                        ),
                        source=source,
                    )
                )
                continue
            results.append(
                self._evaluate_constraint(profile, flags, flag, constraint, identity)
            )
        return results

    def _evaluate_constraint(
        self,
        profile: ApplicationProfile,
        flags: dict[str, FlagValueState],
        flag: FlagValueState,
        c: CapabilityConstraint,
        identity: str,
    ) -> EvaluationFinding:
        expected = _describe_expected(c)
        source = flag.source

        if c.type == "sdk_installed":
            sdks = profile.all_installed_sdks()
            if c.target in sdks:
                return EvaluationFinding(
                    status=EvaluationStatus.PASS,
                    feature_name=flag.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=c.id,
                    expected_requirement=expected,
                    observed_capability=f"sdk {c.target!r} installed",
                    explanation=f"Required SDK {c.target!r} is declared in manifest.",
                    source=source,
                )
            return EvaluationFinding(
                status=EvaluationStatus.UNKNOWN,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"sdk {c.target!r} not declared",
                explanation=(
                    f"Required SDK {c.target!r} is not declared in profile "
                    f"{profile.profile_id!r}."
                ),
                source=source,
            )

        if c.type == "sdk_version":
            observed = profile.sdk_versions.get(c.target)
            if observed is None:
                return EvaluationFinding(
                    status=EvaluationStatus.UNKNOWN,
                    feature_name=flag.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=c.id,
                    expected_requirement=expected,
                    observed_capability=f"sdk_versions[{c.target!r}] missing",
                    explanation=(
                        f"Version for SDK {c.target!r} is not declared in manifest "
                        f"{profile.profile_id!r}."
                    ),
                    source=source,
                )
            ok, detail = _check_value_match(observed, c)
            return EvaluationFinding(
                status=EvaluationStatus.PASS if ok else EvaluationStatus.CONFLICT,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"{c.target}=={observed}",
                explanation=detail,
                source=source,
            )

        if c.type == "backend_api_version":
            observed = profile.backend_api_versions.get(c.target)
            if observed is None:
                return EvaluationFinding(
                    status=EvaluationStatus.UNKNOWN,
                    feature_name=flag.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=c.id,
                    expected_requirement=expected,
                    observed_capability=f"backend_api_versions[{c.target!r}] missing",
                    explanation=f"Backend API version for {c.target!r} is not declared.",
                    source=source,
                )
            ok, detail = _check_value_match(observed, c)
            return EvaluationFinding(
                status=EvaluationStatus.PASS if ok else EvaluationStatus.CONFLICT,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"{c.target}=={observed}",
                explanation=detail,
                source=source,
            )

        if c.type == "app_version":
            ok, detail = _check_value_match(profile.app_version, c)
            return EvaluationFinding(
                status=EvaluationStatus.PASS if ok else EvaluationStatus.CONFLICT,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"app_version=={profile.app_version}",
                explanation=detail,
                source=source,
            )

        if c.type == "native_resource":
            if c.target not in profile.native_resources:
                return EvaluationFinding(
                    status=EvaluationStatus.UNKNOWN,
                    feature_name=flag.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=c.id,
                    expected_requirement=expected,
                    observed_capability=f"native_resources[{c.target!r}] missing",
                    explanation=f"Native resource {c.target!r} is not declared in manifest.",
                    source=source,
                )
            observed = profile.native_resources[c.target]
            if c.equals is not None and isinstance(observed, list):
                ok = c.equals in observed
                detail = (
                    f"{c.equals!r} present in {observed!r}"
                    if ok
                    else f"{c.equals!r} missing from native_resources[{c.target!r}]={observed!r}"
                )
            else:
                ok, detail = _check_value_match(observed, c)
            return EvaluationFinding(
                status=EvaluationStatus.PASS if ok else EvaluationStatus.CONFLICT,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"{c.target}={observed!r}",
                explanation=detail,
                source=source,
            )

        if c.type == "device_capability":
            if c.target not in profile.device_capabilities:
                return EvaluationFinding(
                    status=EvaluationStatus.UNKNOWN,
                    feature_name=flag.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=c.id,
                    expected_requirement=expected,
                    observed_capability=f"device_capabilities[{c.target!r}] missing",
                    explanation=f"Device capability {c.target!r} is not declared in manifest.",
                    source=source,
                )
            observed = profile.device_capabilities[c.target]
            ok, detail = _check_value_match(observed, c)
            return EvaluationFinding(
                status=EvaluationStatus.PASS if ok else EvaluationStatus.CONFLICT,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"{c.target}={observed!r}",
                explanation=detail,
                source=source,
            )

        if c.type == "flag_value":
            ok, detail = _check_value_match(flag.value, c)
            return EvaluationFinding(
                status=EvaluationStatus.PASS if ok else EvaluationStatus.CONFLICT,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"value={flag.value!r}",
                explanation=detail,
                source=source,
            )

        if c.type == "platform_in":
            allowed = [str(v).lower() for v in (c.in_values or [])]
            ok = profile.platform in allowed
            return EvaluationFinding(
                status=EvaluationStatus.PASS if ok else EvaluationStatus.CONFLICT,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"platform={profile.platform!r}",
                explanation=(
                    f"Platform {profile.platform!r} allowed"
                    if ok
                    else f"Platform {profile.platform!r} not in {allowed!r}"
                ),
                source=source,
            )

        if c.type == "incompatible_with":
            other = flags.get(c.target)
            if other is None or not other.enabled:
                return EvaluationFinding(
                    status=EvaluationStatus.PASS,
                    feature_name=flag.feature_name,
                    identity=identity,
                    profile_id=profile.profile_id,
                    rule_id=c.id,
                    expected_requirement=expected,
                    observed_capability=f"{c.target} disabled/absent",
                    explanation=f"Conflicting feature {c.target!r} is not enabled.",
                    source=source,
                )
            return EvaluationFinding(
                status=EvaluationStatus.CONFLICT,
                feature_name=flag.feature_name,
                identity=identity,
                profile_id=profile.profile_id,
                rule_id=c.id,
                expected_requirement=expected,
                observed_capability=f"{c.target} enabled (value={other.value!r})",
                explanation=(
                    f"Feature {flag.feature_name!r} cannot be enabled alongside "
                    f"{c.target!r} for identity {identity!r}."
                ),
                source=source,
            )

        return EvaluationFinding(
            status=EvaluationStatus.UNKNOWN,
            feature_name=flag.feature_name,
            identity=identity,
            profile_id=profile.profile_id,
            rule_id=c.id,
            expected_requirement=expected,
            observed_capability="unsupported constraint",
            explanation=f"Unsupported constraint type: {c.type!r}",
            source=source,
        )

    def run_validation(
        self,
        evaluations: list[tuple[ApplicationProfile, str, dict[str, FlagValueState]]],
        ruleset: RuleSet,
        environment: str,
        strict: bool = False,
        run_id: str | None = None,
    ) -> ValidationReport:
        """Run validation across a list of (profile, identity, flags) tuples."""
        if not evaluations:
            raise ValueError("Cannot run validation with zero evaluated profiles.")
        if not ruleset.rules:
            raise ValueError("Cannot run validation with an empty ruleset.")

        findings: list[EvaluationFinding] = []
        for profile, identity, flags in evaluations:
            findings.extend(self.evaluate_profile(profile, flags, ruleset, identity))

        if not findings:
            raise ValueError("Validation produced zero findings; refusing empty approval.")

        passed = sum(1 for f in findings if f.status == EvaluationStatus.PASS)
        conflicts = sum(1 for f in findings if f.status == EvaluationStatus.CONFLICT)
        unknowns = sum(1 for f in findings if f.status == EvaluationStatus.UNKNOWN)
        skipped = sum(1 for f in findings if f.status == EvaluationStatus.SKIPPED)
        blocking = conflicts > 0 or (strict and unknowns > 0)

        return ValidationReport(
            run_id=run_id or str(uuid.uuid4()),
            environment=environment,
            strict=strict,
            total_checks=len(findings),
            passed=passed,
            conflicts=conflicts,
            unknowns=unknowns,
            skipped=skipped,
            blocking=blocking,
            findings=findings,
        )
