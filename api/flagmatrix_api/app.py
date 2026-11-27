"""FastAPI adapter over flagmatrix_core."""

from __future__ import annotations

import ipaddress
import os
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from flagmatrix_api.state import AppState, ValidationRecord
from flagmatrix_core import (
    ApplicationProfile,
    ConfigurationTestingEngine,
    EnvironmentComparisonReport,
    FlagsmithConnectionError,
    RuleSet,
    build_identity_and_traits,
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
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

state = AppState()


def _validate_flagsmith_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="Flagsmith URL must be a valid http:// or https:// URL.",
        )
    host = parsed.hostname.lower()
    allow_remote = os.environ.get("FLAGSMITH_ALLOW_REMOTE_URL", "").lower() in {"1", "true", "yes"}
    if not allow_remote and host not in {"localhost", "127.0.0.1", "flagsmith"}:
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_link_local or ip.is_multicast:
                raise HTTPException(status_code=400, detail="Blocked link-local or multicast host.")
        except ValueError:
            pass
        raise HTTPException(
            status_code=400,
            detail=(
                "Remote Flagsmith URLs are disabled by default; set "
                "FLAGSMITH_ALLOW_REMOTE_URL=1 to allow non-localhost targets."
            ),
        )
    return raw_url.strip().rstrip("/")


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
    flagsmith_status: dict[str, Any]
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
    return {
        "status": "error" if state.startup_error else "ok",
        "startup_error": state.startup_error,
        "flagsmith": flagsmith_status,
    }


@app.post("/api/v1/connection")
def update_connection(req: ConnectionUpdateRequest) -> dict[str, Any]:
    validated_url = _validate_flagsmith_url(req.url)
    state.flagsmith_url = validated_url
    if req.api_key is not None and req.api_key.strip():
        state.flagsmith_api_key = req.api_key.strip()
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
        return [
            {"id": e.id, "name": e.name, "project": e.project}
            for e in state.get_client().list_environments(project_id)
        ]
    except FlagsmithConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/profiles")
def get_profiles() -> list[ApplicationProfile]:
    if state.startup_error:
        raise HTTPException(status_code=500, detail=state.startup_error)
    return state.profiles


@app.post("/api/v1/profiles")
def upsert_profile(profile: ApplicationProfile) -> ApplicationProfile:
    state.profiles = [p for p in state.profiles if p.profile_id != profile.profile_id]
    state.profiles.append(profile)
    return profile


@app.get("/api/v1/rules")
def get_rules() -> RuleSet:
    if state.startup_error:
        raise HTTPException(status_code=500, detail=state.startup_error)
    if state.ruleset is None:
        raise HTTPException(status_code=404, detail="No ruleset loaded.")
    return state.ruleset


@app.put("/api/v1/rules")
def update_rules(ruleset: RuleSet) -> RuleSet:
    state.ruleset = ruleset
    return state.ruleset


@app.post("/api/v1/validation/run", response_model=ValidationRecord)
def run_validation(req: ValidationRunRequest) -> ValidationRecord:
    if state.startup_error:
        raise HTTPException(status_code=500, detail=state.startup_error)
    if state.ruleset is None:
        raise HTTPException(status_code=400, detail="No compatibility ruleset loaded.")
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
            identity, traits = build_identity_and_traits(profile, ephemeral=True)
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
    if state.startup_error:
        raise HTTPException(status_code=500, detail=state.startup_error)
    if state.ruleset is None:
        raise HTTPException(status_code=400, detail="No compatibility ruleset loaded.")
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
            identity, traits = build_identity_and_traits(profile, ephemeral=True)
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
