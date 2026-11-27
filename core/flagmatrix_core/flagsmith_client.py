"""Self-hosted Flagsmith REST API and official SDK client with secret redaction."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from flagsmith import Flagsmith
from pydantic import BaseModel

from flagmatrix_core.models import FlagValueState

logger = logging.getLogger("flagmatrix_core.flagsmith")


def redact_secret(secret: str | None) -> str:
    """Redact API keys and tokens so secrets never appear in logs or reports."""
    if not secret:
        return "<empty>"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


class FlagsmithProject(BaseModel):
    id: int
    name: str
    organisation: int | None = None


class FlagsmithEnvironment(BaseModel):
    id: int
    name: str
    api_key: str
    project: int


class FlagsmithFeature(BaseModel):
    id: int
    name: str
    type: str = "STANDARD"
    default_enabled: bool = False
    initial_value: Any = None


class FlagsmithConnectionError(RuntimeError):
    """Raised when connecting to or querying Flagsmith fails."""


class FlagsmithClient:
    """Adapter over Flagsmith Admin REST API and official Python SDK."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        auth_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._auth_token = auth_token
        self._timeout = timeout

    def _admin_headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Authorization": f"Api-Key {self._api_key}"}
        if self._auth_token:
            return {"Authorization": f"Token {self._auth_token}"}
        raise FlagsmithConnectionError(
            "Admin API key or auth token is required for management endpoints."
        )

    def _request_json(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        logger.debug(
            "Flagsmith GET %s (credential=%s)",
            url,
            redact_secret(self._api_key or self._auth_token),
        )
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url, headers=self._admin_headers())
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise FlagsmithConnectionError(
                f"Flagsmith API request failed for {path}: {exc}"
            ) from exc

    def check_health(self) -> dict[str, Any]:
        """Verify liveness and return /version/ metadata."""
        try:
            with httpx.Client(timeout=self._timeout) as client:
                live = client.get(f"{self.base_url}/health/liveness/")
                live.raise_for_status()
                ver = client.get(f"{self.base_url}/version/")
                ver.raise_for_status()
                return ver.json()
        except httpx.HTTPError as exc:
            raise FlagsmithConnectionError(
                f"Unable to reach Flagsmith at {self.base_url}: {exc}"
            ) from exc

    def list_projects(self) -> list[FlagsmithProject]:
        data = self._request_json("/api/v1/projects/")
        items = data.get("results", data) if isinstance(data, dict) else data
        return [FlagsmithProject.model_validate(item) for item in items]

    def list_environments(self, project_id: int) -> list[FlagsmithEnvironment]:
        data = self._request_json(f"/api/v1/environments/?project={project_id}")
        items = data.get("results", data) if isinstance(data, dict) else data
        return [FlagsmithEnvironment.model_validate(item) for item in items]

    def list_features(self, project_id: int) -> list[FlagsmithFeature]:
        data = self._request_json(f"/api/v1/projects/{project_id}/features/")
        items = data.get("results", data) if isinstance(data, dict) else data
        return [FlagsmithFeature.model_validate(item) for item in items]

    def get_environment_flags(self, environment_key: str) -> dict[str, FlagValueState]:
        """Evaluate environment default flags via official Flagsmith SDK."""
        sdk = Flagsmith(
            environment_key=environment_key,
            api_url=f"{self.base_url}/api/v1/",
            request_timeout_seconds=int(self._timeout),
        )
        flags = sdk.get_environment_flags()
        return self._convert_sdk_flags(flags, identity="__environment_default__")

    def get_identity_flags(
        self,
        environment_key: str,
        identifier: str,
        traits: dict[str, Any] | None = None,
    ) -> dict[str, FlagValueState]:
        """Evaluate effective flags for a specific identity + traits via official SDK."""
        sdk = Flagsmith(
            environment_key=environment_key,
            api_url=f"{self.base_url}/api/v1/",
            request_timeout_seconds=int(self._timeout),
        )
        flags = sdk.get_identity_flags(identifier=identifier, traits=traits or {})
        return self._convert_sdk_flags(flags, identity=identifier)

    @staticmethod
    def _convert_sdk_flags(flags_obj: Any, identity: str) -> dict[str, FlagValueState]:
        result: dict[str, FlagValueState] = {}
        for name, flag in flags_obj.flags.items():
            result[name] = FlagValueState(
                feature_name=name,
                enabled=bool(flag.enabled),
                value=flag.value,
                source="flagsmith",
                identity=identity,
            )
        return result
