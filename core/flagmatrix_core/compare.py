"""Environment comparison logic built on top of CompatibilityEngine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from flagmatrix_core.engine import CompatibilityEngine
from flagmatrix_core.models import (
    ApplicationProfile,
    EvaluationStatus,
    FlagValueState,
    RuleSet,
    ValidationReport,
)


class FlagDiff(BaseModel):
    profile_id: str
    identity: str
    feature_name: str
    source_enabled: bool | None
    target_enabled: bool | None
    source_value: Any = None
    target_value: Any = None


class EnvironmentComparisonReport(BaseModel):
    source_environment: str
    target_environment: str
    flag_diffs: list[FlagDiff] = Field(default_factory=list)
    source_report: ValidationReport
    target_report: ValidationReport
    new_conflicts_in_target: int
    new_unknowns_in_target: int
    new_conflict_keys: list[str] = Field(default_factory=list)
    new_unknown_keys: list[str] = Field(default_factory=list)


def _finding_key(profile_id: str, identity: str, feature_name: str, rule_id: str) -> str:
    return f"{profile_id}|{identity}|{feature_name}|{rule_id}"


def compare_environments(
    source_env: str,
    target_env: str,
    source_evaluations: list[tuple[ApplicationProfile, str, dict[str, FlagValueState]]],
    target_evaluations: list[tuple[ApplicationProfile, str, dict[str, FlagValueState]]],
    ruleset: RuleSet,
    strict: bool = False,
) -> EnvironmentComparisonReport:
    """Compare flag states and compatibility findings across all profiles/identities."""
    engine = CompatibilityEngine()
    src_report = engine.run_validation(source_evaluations, ruleset, source_env, strict=strict)
    tgt_report = engine.run_validation(target_evaluations, ruleset, target_env, strict=strict)

    src_map = {
        (profile.profile_id, identity): flags
        for profile, identity, flags in source_evaluations
    }
    tgt_map = {
        (profile.profile_id, identity): flags
        for profile, identity, flags in target_evaluations
    }
    all_pairs = sorted(set(src_map.keys()) | set(tgt_map.keys()))

    diffs: list[FlagDiff] = []
    for profile_id, identity in all_pairs:
        src_flags = src_map.get((profile_id, identity), {})
        tgt_flags = tgt_map.get((profile_id, identity), {})
        all_names = sorted(set(src_flags.keys()) | set(tgt_flags.keys()))
        for name in all_names:
            sf = src_flags.get(name)
            tf = tgt_flags.get(name)
            s_en = sf.enabled if sf else None
            t_en = tf.enabled if tf else None
            s_val = sf.value if sf else None
            t_val = tf.value if tf else None
            if s_en != t_en or s_val != t_val:
                diffs.append(
                    FlagDiff(
                        profile_id=profile_id,
                        identity=identity,
                        feature_name=name,
                        source_enabled=s_en,
                        target_enabled=t_en,
                        source_value=s_val,
                        target_value=t_val,
                    )
                )

    src_conflicts = {
        _finding_key(f.profile_id, f.identity, f.feature_name, f.rule_id)
        for f in src_report.findings
        if f.status == EvaluationStatus.CONFLICT
    }
    tgt_conflicts = {
        _finding_key(f.profile_id, f.identity, f.feature_name, f.rule_id)
        for f in tgt_report.findings
        if f.status == EvaluationStatus.CONFLICT
    }
    src_unknowns = {
        _finding_key(f.profile_id, f.identity, f.feature_name, f.rule_id)
        for f in src_report.findings
        if f.status == EvaluationStatus.UNKNOWN
    }
    tgt_unknowns = {
        _finding_key(f.profile_id, f.identity, f.feature_name, f.rule_id)
        for f in tgt_report.findings
        if f.status == EvaluationStatus.UNKNOWN
    }

    new_conflict_keys = sorted(tgt_conflicts - src_conflicts)
    new_unknown_keys = sorted(tgt_unknowns - src_unknowns)

    return EnvironmentComparisonReport(
        source_environment=source_env,
        target_environment=target_env,
        flag_diffs=diffs,
        source_report=src_report,
        target_report=tgt_report,
        new_conflicts_in_target=len(new_conflict_keys),
        new_unknowns_in_target=len(new_unknown_keys),
        new_conflict_keys=new_conflict_keys,
        new_unknown_keys=new_unknown_keys,
    )
