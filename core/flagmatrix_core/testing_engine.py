"""Configuration testing engine with boundary, regression, and pairwise coverage."""

from __future__ import annotations

import itertools
from typing import Any

from pydantic import BaseModel, Field

from flagmatrix_core.engine import CompatibilityEngine
from flagmatrix_core.models import (
    ApplicationProfile,
    FlagValueState,
    RuleSet,
    ValidationReport,
)


class TestCaseSpec(BaseModel):
    """Explicit test case for a profile + identity (and optional hypothetical overrides)."""

    name: str
    profile: ApplicationProfile
    identity: str
    traits: dict[str, Any] = Field(default_factory=dict)
    hypothetical_overrides: dict[str, FlagValueState] | None = None


class CoverageSummary(BaseModel):
    """Coverage metrics reported by the configuration testing engine."""

    flagsmith_cases: int
    hypothetical_cases: int
    total_cases: int
    pairwise_features_covered: list[str] = Field(default_factory=list)
    total_pairs: int = 0
    covered_pairs: int = 0
    achieved_pairwise_coverage: float = 0.0
    exhaustive: bool = False


class TestRunResult(BaseModel):
    """Combined validation report and coverage summary."""

    report: ValidationReport
    coverage: CoverageSummary


def generate_pairwise_flag_configs(
    feature_domains: dict[str, list[tuple[bool, Any]]],
    forbidden_pairs: list[tuple[str, bool, str, bool]] | None = None,
) -> tuple[list[dict[str, FlagValueState]], int, int]:
    """Generate constrained pairwise hypothetical flag configurations via greedy cover.

    Returns (configs, covered_pairs_count, total_valid_pairs_count).
    """
    features = sorted(feature_domains.keys())
    if len(features) < 2:
        single = [
            {
                features[0]: FlagValueState(
                    feature_name=features[0],
                    enabled=en,
                    value=val,
                    source="hypothetical",
                    identity="__hypothetical__",
                )
            }
            for en, val in (feature_domains[features[0]] if features else [])
        ]
        return single, len(single), len(single)

    forbidden = set(forbidden_pairs or [])

    def is_valid_pair(f1: str, v1: tuple[bool, Any], f2: str, v2: tuple[bool, Any]) -> bool:
        return (
            (f1, v1[0], f2, v2[0]) not in forbidden
            and (f2, v2[0], f1, v1[0]) not in forbidden
        )

    all_pairs: set[tuple[str, int, str, int]] = set()
    for i, f1 in enumerate(features):
        for f2 in features[i + 1 :]:
            for idx1, v1 in enumerate(feature_domains[f1]):
                for idx2, v2 in enumerate(feature_domains[f2]):
                    if is_valid_pair(f1, v1, f2, v2):
                        all_pairs.add((f1, idx1, f2, idx2))

    uncovered = set(all_pairs)
    chosen_indices: list[dict[str, int]] = []

    all_candidates = list(
        itertools.product(*(range(len(feature_domains[f])) for f in features))
    )
    valid_candidates: list[dict[str, int]] = []
    for cand in all_candidates:
        mapping = dict(zip(features, cand))
        ok = True
        for i, f1 in enumerate(features):
            for f2 in features[i + 1 :]:
                if not is_valid_pair(
                    f1,
                    feature_domains[f1][mapping[f1]],
                    f2,
                    feature_domains[f2][mapping[f2]],
                ):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            valid_candidates.append(mapping)

    while uncovered and valid_candidates:
        best_cand = max(
            valid_candidates,
            key=lambda c: sum(
                1
                for i, f1 in enumerate(features)
                for f2 in features[i + 1 :]
                if (f1, c[f1], f2, c[f2]) in uncovered
            ),
        )
        newly_covered = {
            (f1, best_cand[f1], f2, best_cand[f2])
            for i, f1 in enumerate(features)
            for f2 in features[i + 1 :]
        } & uncovered
        if not newly_covered:
            break
        uncovered -= newly_covered
        chosen_indices.append(best_cand)

    configs: list[dict[str, FlagValueState]] = []
    for idx, mapping in enumerate(chosen_indices):
        cfg: dict[str, FlagValueState] = {}
        for fname, val_idx in mapping.items():
            enabled, val = feature_domains[fname][val_idx]
            cfg[fname] = FlagValueState(
                feature_name=fname,
                enabled=enabled,
                value=val,
                source="hypothetical",
                identity=f"hypothetical-{idx + 1}",
            )
        configs.append(cfg)

    covered = len(all_pairs) - len(uncovered)
    return configs, covered, len(all_pairs)


class ConfigurationTestingEngine:
    """Runs validation across Flagsmith evaluations and optional hypothetical cases."""

    def __init__(self, compatibility_engine: CompatibilityEngine | None = None) -> None:
        self._engine = compatibility_engine or CompatibilityEngine()

    def run_suite(
        self,
        flagsmith_cases: list[tuple[ApplicationProfile, str, dict[str, FlagValueState]]],
        ruleset: RuleSet,
        environment: str,
        strict: bool = False,
        hypothetical_cases: list[tuple[ApplicationProfile, str, dict[str, FlagValueState]]] | None = None,
        pairwise_features: list[str] | None = None,
        covered_pairs: int = 0,
        total_pairs: int = 0,
    ) -> TestRunResult:
        hypo = hypothetical_cases or []
        combined = list(flagsmith_cases) + list(hypo)
        report = self._engine.run_validation(combined, ruleset, environment, strict=strict)

        coverage_pct = (covered_pairs / total_pairs * 100.0) if total_pairs > 0 else 0.0
        total_possible_full = 2 ** len(pairwise_features or [])
        is_exhaustive = bool(
            total_pairs > 0 and covered_pairs == total_pairs and len(hypo) >= total_possible_full
        )

        coverage = CoverageSummary(
            flagsmith_cases=len(flagsmith_cases),
            hypothetical_cases=len(hypo),
            total_cases=len(combined),
            pairwise_features_covered=pairwise_features or [],
            total_pairs=total_pairs,
            covered_pairs=covered_pairs,
            achieved_pairwise_coverage=round(coverage_pct, 2),
            exhaustive=is_exhaustive,
        )
        return TestRunResult(report=report, coverage=coverage)
