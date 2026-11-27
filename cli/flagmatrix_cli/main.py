"""FlagMatrix CLI — connect, validate, compare, report, and init."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from flagmatrix_cli.config import FlagMatrixConfig, FlagsmithConfig, load_config
from flagmatrix_core import (
    CompatibilityEngine,
    EvaluationStatus,
    FlagsmithClient,
    FlagsmithConnectionError,
    MalformedVersionError,
    ManifestValidationError,
    ValidationReport,
    build_identity_and_traits,
    compare_environments,
    load_profiles,
    load_ruleset,
    redact_secret,
)

app = typer.Typer(
    name="flagmatrix",
    help="Deterministic feature configuration compatibility toolkit for Flagsmith.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

EXIT_OK = 0
EXIT_CONFLICT = 1
EXIT_ERROR = 2


def _resolve_client(
    url: Optional[str],
    api_key: Optional[str],
    cfg: Optional[FlagMatrixConfig],
) -> FlagsmithClient:
    base_url = (
        url
        if url is not None
        else (cfg.flagsmith.url if cfg else os.environ.get("FLAGSMITH_API_URL", "http://localhost:8000"))
    ).rstrip("/")
    key = (
        cfg.flagsmith.resolve_api_key(explicit_key=api_key, target_url=base_url)
        if cfg
        else FlagsmithConfig(url=base_url).resolve_api_key(explicit_key=api_key, target_url=base_url)
    )
    return FlagsmithClient(base_url=base_url, api_key=key)


def _render_report_table(report: ValidationReport) -> None:
    table = Table(title=f"FlagMatrix Validation ({report.environment})")
    table.add_column("Status", style="bold")
    table.add_column("Feature")
    table.add_column("Identity")
    table.add_column("Profile")
    table.add_column("Rule")
    table.add_column("Explanation")

    color_map = {
        EvaluationStatus.PASS: "green",
        EvaluationStatus.CONFLICT: "red",
        EvaluationStatus.UNKNOWN: "yellow",
        EvaluationStatus.SKIPPED: "dim",
    }
    for f in report.findings:
        color = color_map[f.status]
        table.add_row(
            f"[{color}]{f.status.value}[/{color}]",
            f.feature_name,
            f.identity,
            f.profile_id,
            f.rule_id,
            f.explanation,
        )
    console.print(table)
    console.print(
        f"Summary: total={report.total_checks} pass={report.passed} "
        f"conflicts={report.conflicts} unknown={report.unknowns} "
        f"skipped={report.skipped} blocking={report.blocking}"
    )


@app.command()
def init(
    directory: Path = typer.Option(Path("."), "--dir", "-d", help="Target directory"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
) -> None:
    """Scaffold a starter flagmatrix.yaml, profiles/, and rules.yaml."""
    directory.mkdir(parents=True, exist_ok=True)
    profiles_dir = directory / "profiles"
    profiles_dir.mkdir(exist_ok=True)

    cfg_path = directory / "flagmatrix.yaml"
    profile_path = profiles_dir / "sample_android.yaml"
    rules_path = directory / "rules.yaml"

    files = {
        cfg_path: (
            'schema_version: "1.0"\n'
            "flagsmith:\n"
            "  url: http://localhost:8000\n"
            "  api_key_env: FLAGSMITH_API_KEY_localhost_8000\n"
            "project_id: 1\n"
            "environment: Development\n"
            "profiles_path: profiles\n"
            "rules_path: rules.yaml\n"
            "strict: false\n"
        ),
        profile_path: (
            'schema_version: "1.0"\n'
            "app_id: com.example.fintech\n"
            "tenant_id: sample_tenant\n"
            "platform: android\n"
            'app_version: "1.0.0"\n'
            "build_flavor: production\n"
            "environment: Development\n"
            "installed_sdks:\n"
            "  - stripe_sdk\n"
            "sdk_versions:\n"
            '  stripe_sdk: "3.0.0"\n'
            "backend_api_versions:\n"
            '  payments: "2.0.0"\n'
            "native_resources:\n"
            "  launcher_icons:\n"
            "    - ic_launcher\n"
            "device_capabilities:\n"
            "  biometrics: true\n"
        ),
        rules_path: (
            'schema_version: "1.0"\n'
            "rules:\n"
            "  - feature_name: instant_payouts\n"
            "    constraints:\n"
            "      - id: stripe-min-v3\n"
            "        type: sdk_version\n"
            "        target: stripe_sdk\n"
            '        min_version: "3.0.0"\n'
        ),
    }

    created: list[str] = []
    for path, content in files.items():
        if path.exists() and not force:
            continue
        path.write_text(content, encoding="utf-8")
        created.append(str(path))

    console.print(f"Initialized FlagMatrix files: {created or 'all files already exist'}")


@app.command()
def connect(
    url: Optional[str] = typer.Option(None, "--url", help="Flagsmith base URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Flagsmith API key"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to flagmatrix.yaml"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Verify connectivity to self-hosted Flagsmith and list projects/environments."""
    try:
        cfg = load_config(config) if config else None
        client = _resolve_client(url, api_key, cfg)
        version = client.check_health()
        projects = client.list_projects()
        envs_by_project = {
            p.id: [
                {"id": e.id, "name": e.name, "project": e.project}
                for e in client.list_environments(p.id)
            ]
            for p in projects
        }
    except (ManifestValidationError, FlagsmithConnectionError, ValueError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR)

    payload = {
        "url": client.base_url,
        "credential": redact_secret(client._api_key),
        "version": version.get("image_tag"),
        "experimentation_enabled": version.get("experimentation_enabled"),
        "projects": [p.model_dump() for p in projects],
        "environments": envs_by_project,
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(
            f"[green]Connected[/green] to {client.base_url} "
            f"(version={payload['version']}, key={payload['credential']})"
        )
        for p in projects:
            env_names = ", ".join(e["name"] for e in envs_by_project[p.id])
            console.print(f"  Project [{p.id}] {p.name}: {env_names}")


@app.command()
def validate(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to flagmatrix.yaml"),
    profiles: Optional[Path] = typer.Option(None, "--profiles", "-p", help="Profile file or directory"),
    rules: Optional[Path] = typer.Option(None, "--rules", "-r", help="Rules YAML file"),
    env: Optional[str] = typer.Option(None, "--env", "-e", help="Flagsmith environment name"),
    project_id: Optional[int] = typer.Option(None, "--project-id", help="Flagsmith project ID"),
    url: Optional[str] = typer.Option(None, "--url", help="Flagsmith base URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Flagsmith API key"),
    strict: Optional[bool] = typer.Option(None, "--strict/--no-strict", help="Treat UNKNOWN as blocking"),
    ephemeral: bool = typer.Option(True, "--ephemeral/--no-ephemeral", help="Use isolated transient evaluation identities"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
    report_out: Optional[Path] = typer.Option(None, "--report-out", help="Write JSON report to file"),
) -> None:
    """Validate application capability profiles against Flagsmith feature states."""
    try:
        cfg = load_config(config) if config is not None else (
            load_config(Path("flagmatrix.yaml")) if Path("flagmatrix.yaml").exists() else None
        )
        prof_path = profiles if profiles is not None else (cfg.resolve_path(cfg.profiles_path) if cfg else None)
        rules_path = rules if rules is not None else (cfg.resolve_path(cfg.rules_path) if cfg else None)
        env_name = env if env is not None else (cfg.environment if cfg else "Development")
        proj_id = project_id if project_id is not None else (cfg.project_id if cfg else 1)
        is_strict = strict if strict is not None else (cfg.strict if cfg else False)

        if not prof_path or not rules_path:
            raise ValueError("Both --profiles and --rules (or flagmatrix.yaml) are required.")

        loaded_profiles = load_profiles(prof_path)
        ruleset = load_ruleset(rules_path)

        client = _resolve_client(url, api_key, cfg)
        envs = client.list_environments(proj_id)
        target_env = next((e for e in envs if e.name.lower() == env_name.lower()), None)
        if target_env is None:
            raise FlagsmithConnectionError(
                f"Environment {env_name!r} not found in project {proj_id}."
            )

        evaluations = []
        for profile in loaded_profiles:
            identity, traits = build_identity_and_traits(profile, ephemeral=ephemeral)
            flags = client.get_identity_flags(
                target_env.api_key, identifier=identity, traits=traits
            )
            evaluations.append((profile, identity, flags))

        engine = CompatibilityEngine()
        report = engine.run_validation(
            evaluations, ruleset, environment=target_env.name, strict=is_strict
        )
    except (ManifestValidationError, FlagsmithConnectionError, MalformedVersionError, ValueError) as exc:
        err_console.print(f"[red]Configuration/Execution Error:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR)

    if report_out:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    if json_output:
        typer.echo(report.model_dump_json(indent=2))
    else:
        _render_report_table(report)

    raise typer.Exit(code=EXIT_CONFLICT if report.blocking else EXIT_OK)


@app.command()
def compare(
    source_env: str = typer.Option(..., "--source", help="Source environment name"),
    target_env: str = typer.Option(..., "--target", help="Target environment name"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to flagmatrix.yaml"),
    profiles: Optional[Path] = typer.Option(None, "--profiles", "-p", help="Profile file or directory"),
    rules: Optional[Path] = typer.Option(None, "--rules", "-r", help="Rules YAML file"),
    project_id: Optional[int] = typer.Option(None, "--project-id", help="Flagsmith project ID"),
    url: Optional[str] = typer.Option(None, "--url", help="Flagsmith base URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Flagsmith API key"),
    strict: Optional[bool] = typer.Option(None, "--strict/--no-strict", help="Treat UNKNOWN as blocking"),
    ephemeral: bool = typer.Option(True, "--ephemeral/--no-ephemeral", help="Use isolated transient evaluation identities"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Compare feature compatibility between two Flagsmith environments."""
    try:
        cfg = load_config(config) if config is not None else (
            load_config(Path("flagmatrix.yaml")) if Path("flagmatrix.yaml").exists() else None
        )
        prof_path = profiles if profiles is not None else (cfg.resolve_path(cfg.profiles_path) if cfg else None)
        rules_path = rules if rules is not None else (cfg.resolve_path(cfg.rules_path) if cfg else None)
        proj_id = project_id if project_id is not None else (cfg.project_id if cfg else 1)
        is_strict = strict if strict is not None else (cfg.strict if cfg else False)
        if not prof_path or not rules_path:
            raise ValueError("Both --profiles and --rules (or flagmatrix.yaml) are required.")

        loaded_profiles = load_profiles(prof_path)
        ruleset = load_ruleset(rules_path)
        client = _resolve_client(url, api_key, cfg)
        envs = client.list_environments(proj_id)

        src = next((e for e in envs if e.name.lower() == source_env.lower()), None)
        tgt = next((e for e in envs if e.name.lower() == target_env.lower()), None)
        if not src or not tgt:
            raise FlagsmithConnectionError(
                f"Could not find both {source_env!r} and {target_env!r} in project {proj_id}."
            )

        src_evals = []
        tgt_evals = []
        for profile in loaded_profiles:
            identity, traits = build_identity_and_traits(profile, ephemeral=ephemeral)
            src_evals.append((profile, identity, client.get_identity_flags(src.api_key, identity, traits)))
            tgt_evals.append((profile, identity, client.get_identity_flags(tgt.api_key, identity, traits)))

        comparison = compare_environments(
            src.name, tgt.name, src_evals, tgt_evals, ruleset, strict=is_strict
        )
    except (ManifestValidationError, FlagsmithConnectionError, MalformedVersionError, ValueError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR)

    if json_output:
        typer.echo(comparison.model_dump_json(indent=2))
    else:
        console.print(
            f"Comparison {comparison.source_environment} -> {comparison.target_environment}: "
            f"{len(comparison.flag_diffs)} flag diffs, "
            f"new_conflicts={comparison.new_conflicts_in_target}, "
            f"new_unknowns={comparison.new_unknowns_in_target}"
        )
    raise typer.Exit(code=EXIT_CONFLICT if comparison.target_report.blocking else EXIT_OK)


@app.command()
def report(
    report_file: Path = typer.Argument(..., help="Path to saved JSON ValidationReport"),
    output_format: str = typer.Option("text", "--format", "-f", help="text|json|markdown"),
) -> None:
    """Render a saved FlagMatrix JSON validation report."""
    if not report_file.exists():
        err_console.print(f"[red]Error:[/red] Report file not found: {report_file}")
        raise typer.Exit(code=EXIT_ERROR)
    try:
        parsed = ValidationReport.model_validate_json(report_file.read_text(encoding="utf-8"))
    except Exception as exc:
        err_console.print(f"[red]Invalid report file:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR)

    fmt = output_format.lower()
    if fmt == "json":
        typer.echo(parsed.model_dump_json(indent=2))
    elif fmt == "markdown":
        lines = [
            f"# FlagMatrix Report (`{parsed.environment}`)",
            "",
            f"- **Total:** {parsed.total_checks} | **Pass:** {parsed.passed} | "
            f"**Conflicts:** {parsed.conflicts} | **Unknown:** {parsed.unknowns} | "
            f"**Skipped:** {parsed.skipped} | **Blocking:** {parsed.blocking}",
            "",
            "| Status | Feature | Identity | Rule | Explanation |",
            "|---|---|---|---|---|",
        ]
        for item in parsed.findings:
            lines.append(
                f"| {item.status.value} | `{item.feature_name}` | `{item.identity}` | "
                f"`{item.rule_id}` | {item.explanation} |"
            )
        typer.echo("\n".join(lines))
    else:
        _render_report_table(parsed)
