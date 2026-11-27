"""FastAPI adapter over flagmatrix_core."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from flagmatrix_api.state import AppState, ValidationRecord
from flagmatrix_core import (
    ApplicationProfile,
    ConfigurationTestingEngine,
    EnvironmentComparisonReport,
    FlagsmithConnectionError,
    RuleSet,
    compare_environments,
    redact_secret,
)

app = FastAPI(
    title="FlagMatrix API",
    version="0.1.0",
    description="FastAPI adapter over flagmatrix_core for self-hosted Flagsmith compatibility.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

state = AppState()


class ConnectionUpdateRequest(BaseModel):
    url: str
    api_key: Optional[str] = None


class ValidationRunRequest(BaseModel):
    project_id: int = 1
    environment: str = "Development"
    strict: bool = False
    profile_ids: Optional[list[str]] = None
    include_pairwise: bool = False


class CompareEnvironmentsRequest(BaseModel):
    project_id: int = 1
    source_environment: str
    target_environment: str
    strict: bool = False
    profile_ids: Optional[list[str]] = None


@app.get("/health")
def get_health() -> dict[str, Any]:
    flagsmith_status: dict[str, Any] = {"connected": False}
    try:
        version = state.get_client().check_health()
        flagsmith_status = {
            "connected": True,
            "url": state.flagsmith_url,
            "version": version.get("image_tag"),
            "experimentation_enabled": version.get("experimentation_enabled"),
            "credential": redact_secret(state.flagsmith_api_key),
        }
    except FlagsmithConnectionError as exc:
        flagsmith_status = {
            "connected": False,
            "url": state.flagsmith_url,
            "error": str(exc),
        }
    return {"status": "ok", "flagsmith": flagsmith_status}


@app.post("/api/v1/connection")
def update_connection(req: ConnectionUpdateRequest) -> dict[str, Any]:
    state.flagsmith_url = req.url.rstrip("/")
    if req.api_key is not None:
        state.flagsmith_api_key = req.api_key
    try:
        version = state.get_client().check_health()
    except FlagsmithConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "connected": True,
        "url": state.flagsmith_url,
        "version": version.get("image_tag"),
        "experimentation_enabled": version.get("experimentation_enabled"),
        "credential": redact_secret(state.flagsmith_api_key),
    }


@app.get("/api/v1/projects")
def list_projects() -> list[dict[str, Any]]:
    try:
        return [p.model_dump() for p in state.get_client().list_projects()]
    except FlagsmithConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/environments")
def list_environments(project_id: int = Query(1, ge=1)) -> list[dict[str, Any]]:
    try:
        return [e.model_dump() for e in state.get_client().list_environments(project_id)]
    except FlagsmithConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/profiles")
def get_profiles() -> list[ApplicationProfile]:
    return state.profiles


@app.post("/api/v1/profiles")
def upsert_profile(profile: ApplicationProfile) -> ApplicationProfile:
    state.profiles = [p for p in state.profiles if p.profile_id != profile.profile_id]
    state.profiles.append(profile)
    return profile


@app.get("/api/v1/rules")
def get_rules() -> RuleSet:
    return state.ruleset


@app.put("/api/v1/rules")
def update_rules(ruleset: RuleSet) -> RuleSet:
    state.ruleset = ruleset
    return state.ruleset


@app.post("/api/v1/validation/run", response_model=ValidationRecord)
def run_validation(req: ValidationRunRequest) -> ValidationRecord:
    selected_profiles = state.profiles
    if req.profile_ids:
        wanted = set(req.profile_ids)
        selected_profiles = [p for p in state.profiles if p.profile_id in wanted]
    if not selected_profiles:
        raise HTTPException(status_code=400, detail="No application profiles available.")

    client = state.get_client()
    try:
        envs = client.list_environments(req.project_id)
        target = next(
            (e for e in envs if e.name.lower() == req.environment.lower()), None
        )
        if target is None:
            raise HTTPException(
                status_code=404,
                detail=f"Environment {req.environment!r} not found in project {req.project_id}.",
            )

        evaluations = []
        for profile in selected_profiles:
            identity = f"{profile.tenant_id}_{profile.platform}_{profile.app_version}"
            traits = {
                "tenant_id": profile.tenant_id,
                "platform": profile.platform,
                "app_version": profile.app_version,
                **profile.identity_traits,
            }
            flags = client.get_identity_flags(target.api_key, identity, traits)
            evaluations.append((profile, identity, flags))
    except FlagsmithConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    testing_engine = ConfigurationTestingEngine()
    result = testing_engine.run_suite(
        flagsmith_cases=evaluations,
        ruleset=state.ruleset,
        environment=target.name,
        strict=req.strict,
    )
    return state.save_run(result.report, result.coverage)


@app.get("/api/v1/validation", response_model=list[ValidationRecord])
def list_validation_history() -> list[ValidationRecord]:
    return list(reversed(list(state.history.values())))


@app.get("/api/v1/validation/{run_id}", response_model=ValidationRecord)
def get_validation(run_id: str) -> ValidationRecord:
    record = state.history.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Validation run {run_id!r} not found.")
    return record


@app.post("/api/v1/environments/compare", response_model=EnvironmentComparisonReport)
def compare_envs(req: CompareEnvironmentsRequest) -> EnvironmentComparisonReport:
    selected_profiles = state.profiles
    if req.profile_ids:
        wanted = set(req.profile_ids)
        selected_profiles = [p for p in state.profiles if p.profile_id in wanted]
    if not selected_profiles:
        raise HTTPException(status_code=400, detail="No application profiles available.")

    client = state.get_client()
    try:
        envs = client.list_environments(req.project_id)
        src = next((e for e in envs if e.name.lower() == req.source_environment.lower()), None)
        tgt = next((e for e in envs if e.name.lower() == req.target_environment.lower()), None)
        if not src or not tgt:
            raise HTTPException(status_code=404, detail="Source or target environment not found.")

        src_evals = []
        tgt_evals = []
        for profile in selected_profiles:
            identity = f"{profile.tenant_id}_{profile.platform}_{profile.app_version}"
            traits = {"tenant_id": profile.tenant_id, "platform": profile.platform, **profile.identity_traits}
            src_evals.append((profile, identity, client.get_identity_flags(src.api_key, identity, traits)))
            tgt_evals.append((profile, identity, client.get_identity_flags(tgt.api_key, identity, traits)))
    except FlagsmithConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return compare_environments(
        src.name, tgt.name, src_evals, tgt_evals, state.ruleset, strict=req.strict
    )


@app.get("/api/v1/reports/{run_id}")
def export_report(
    run_id: str,
    format: str = Query("json", pattern="^(json|markdown)$"),
) -> Any:
    record = state.history.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Report {run_id!r} not found.")
    if format == "markdown":
        rep = record.report
        lines = [
            f"# FlagMatrix Report (`{rep.environment}`)",
            "",
            f"- **Run ID:** `{rep.run_id}`",
            f"- **Total:** {rep.total_checks} | **Pass:** {rep.passed} | "
            f"**Conflicts:** {rep.conflicts} | **Unknown:** {rep.unknowns} | "
            f"**Skipped:** {rep.skipped} | **Blocking:** {rep.blocking}",
            "",
            "| Status | Feature | Identity | Profile | Rule | Explanation |",
            "|---|---|---|---|---|---|",
        ]
        for f in rep.findings:
            lines.append(
                f"| {f.status.value} | `{f.feature_name}` | `{f.identity}` | "
                f"`{f.profile_id}` | `{f.rule_id}` | {f.explanation} |"
            )
        return PlainTextResponse("\n".join(lines), media_type="text/markdown")
    return record.model_dump()
