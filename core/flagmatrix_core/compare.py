"""Environment comparison logic built on top of CompatibilityEngine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from flagmatrix_core.engine import CompatibilityEngine
from flagmatrix_core.models import (
    ApplicationProfile,
    FlagValueState,
    RuleSet,
    ValidationReport,
)


class FlagDiff(BaseModel):
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


def compare_environments(
    source_env: str,
    target_env: str,
    source_evaluations: list[tuple[ApplicationProfile, str, dict[str, FlagValueState]]],
    target_evaluations: list[tuple[ApplicationProfile, str, dict[str, FlagValueState]]],
    ruleset: RuleSet,
    strict: bool = False,
) -> EnvironmentComparisonReport:
    """Compare flag states and compatibility reports between two environments."""
    engine = CompatibilityEngine()
    src_report = engine.run_validation(source_evaluations, ruleset, source_env, strict=strict)
    tgt_report = engine.run_validation(target_evaluations, ruleset, target_env, strict=strict)

    src_flags = source_evaluations[0][2] if source_evaluations else {}
    tgt_flags = target_evaluations[0][2] if target_evaluations else {}
    all_names = sorted(set(src_flags.keys()) | set(tgt_flags.keys()))

    diffs: list[FlagDiff] = []
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
                    feature_name=name,
                    source_enabled=s_en,
                    target_enabled=t_en,
                    source_value=s_val,
                    target_value=t_val,
                )
            )

    return EnvironmentComparisonReport(
        source_environment=source_env,
        target_environment=target_env,
        flag_diffs=diffs,
        source_report=src_report,
        target_report=tgt_report,
        new_conflicts_in_target=max(0, tgt_report.conflicts - src_report.conflicts),
        new_unknowns_in_target=max(0, tgt_report.unknowns - src_report.unknowns),
    )
