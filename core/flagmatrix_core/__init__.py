"""FlagMatrix Core — Deterministic feature configuration compatibility engine."""

from flagmatrix_core.compare import EnvironmentComparisonReport, FlagDiff, compare_environments
from flagmatrix_core.engine import CompatibilityEngine
from flagmatrix_core.flagsmith_client import (
    FlagsmithClient,
    FlagsmithConnectionError,
    FlagsmithEnvironment,
    FlagsmithFeature,
    FlagsmithProject,
    redact_secret,
)
from flagmatrix_core.loader import (
    ManifestValidationError,
    load_profile,
    load_profiles,
    load_ruleset,
)
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
from flagmatrix_core.semver import MalformedVersionError, parse_semver, satisfies_version_range
from flagmatrix_core.testing_engine import (
    ConfigurationTestingEngine,
    CoverageSummary,
    TestCaseSpec,
    TestRunResult,
    generate_pairwise_flag_configs,
)

__version__ = "0.1.0"

__all__ = [
    "ApplicationProfile",
    "CapabilityConstraint",
    "CompatibilityEngine",
    "ConfigurationTestingEngine",
    "CoverageSummary",
    "EnvironmentComparisonReport",
    "EvaluationFinding",
    "EvaluationStatus",
    "FeatureRule",
    "FlagDiff",
    "FlagValueState",
    "FlagsmithClient",
    "FlagsmithConnectionError",
    "FlagsmithEnvironment",
    "FlagsmithFeature",
    "FlagsmithProject",
    "MalformedVersionError",
    "ManifestValidationError",
    "RuleSet",
    "TestCaseSpec",
    "TestRunResult",
    "ValidationReport",
    "__version__",
    "compare_environments",
    "generate_pairwise_flag_configs",
    "load_profile",
    "load_profiles",
    "load_ruleset",
    "parse_semver",
    "redact_secret",
    "satisfies_version_range",
]
