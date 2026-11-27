# FlagMatrix — Feature Configuration Compatibility Toolkit

Open-source, deterministic feature configuration compatibility toolkit for **self-hosted Flagsmith** (Toggle Wars 2026 — Track 3).

## Problem Statement & Unique Value Proposition

Feature flag platforms tell you **which flags are enabled for which identities**, but they do not know whether a specific client build, white-label tenant, OS platform, SDK version, native resource, or backend API version can **safely support** those flags. Enabling a flag for an incompatible build causes runtime crashes or broken user flows.

**FlagMatrix** closes this gap deterministically (with zero LLMs or heuristics):
- Evaluates real per-identity flag states from a **self-hosted Flagsmith** instance using the official Flagsmith SDK and REST API.
- Validates effective flag states against versioned **Application Capability Manifests** and declarative **SemVer 2.0.0 Feature Rules**.
- Reports `PASS`, `CONFLICT`, `UNKNOWN` (undeclared capabilities are never assumed available), or `SKIPPED` (disabled flags do not cause false conflicts).
- Enforces release gates in CI/CD with deterministic exit codes (`0`, `1`, `2`) and provides a 10-screen **Flutter Studio** dashboard.

## Architecture

```text
+-----------------------+       +-----------------------+
|   Flutter Studio      |       |   FlagMatrix CLI      |
|  (Web / Windows UI)   |       |  (Typer + Rich)       |
+-----------+-----------+       +-----------+-----------+
            | HTTP (Dio)                    | Python import
            v                               |
+-----------------------+                   |
|   FastAPI Adapter     |                   |
|  (flagmatrix_api)     |                   |
+-----------+-----------+                   |
            | Python import                 |
            v                               v
+-------------------------------------------------------+
|              FlagMatrix Core (flagmatrix_core)        |
|  - Manifest & RuleSet Loaders (Pydantic v2 + YAML)    |
|  - SemVer 2.0.0 Comparator (prerelease & metadata)    |
|  - Deterministic CompatibilityEngine                  |
|  - Environment Comparison (per-finding diffing)       |
|  - FlagsmithClient (REST API + Official Flagsmith SDK)|
+-------------------------------------------------------+
            |
            v
+-------------------------------------------------------+
|           Self-Hosted Flagsmith Instance              |
+-------------------------------------------------------+
```

## Screenshots & Demo Video

- **Demo Video:** _Add your recorded walkthrough link here before submission._
- **Screenshots:** _Add captured screenshots of Flutter Studio (Compatibility Matrix, Conflict Details, Environment Comparison) and CLI output here before submission._

## Windows Setup (From a Fresh Clone)

### 1. Prerequisites
- Python 3.11+
- Flutter 3.41+ (Web / Windows enabled)
- Docker Desktop for Windows (with Docker Compose v2)

### 2. Provision Self-Hosted Flagsmith
```powershell
mkdir flagsmith
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Flagsmith/flagsmith/main/docker-compose.yml" -OutFile "flagsmith\docker-compose.yml"
cd flagsmith
docker compose up -d
```
Wait for `http://localhost:8000/health/liveness/` to return `200`, create your admin account at `http://localhost:8000`, and generate an Organisation Master API Key in Flagsmith Settings.

### 3. Configure Credentials (No Secrets in Source Control)
Store credentials in `flagsmith\flagsmith.env` (gitignored) or set environment variables in your shell:
```powershell
$env:FLAGSMITH_API_URL = "http://localhost:8000"
$env:FLAGSMITH_API_KEY_localhost_8000 = "<your-master-api-key>"
```

### 4. Install FlagMatrix & Seed Demo Data
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python examples\seed_flagsmith.py
```

## CLI Examples & Exit Codes

```powershell
flagmatrix init --dir my-project
flagmatrix connect --url http://localhost:8000 --json
flagmatrix validate --profiles examples\profiles --rules examples\rules.yaml --env Production
flagmatrix compare --source Development --target Production --profiles examples\profiles --rules examples\rules.yaml
flagmatrix report report.json --format markdown
```

| Exit Code | Meaning |
|---|---|
| `0` | Validation passed (no conflicts; no unknowns when `--strict` is set) |
| `1` | Compatibility conflicts (or unknowns in `--strict` mode) block the release |
| `2` | Invalid configuration, malformed manifest/rules, or Flagsmith SDK/API error |

## Live Failure-to-Success Demonstration

1. **Blocked release (`novapay_android.yaml` against `Production`):**
   - `stripe_sdk: 2.1.0 < 3.0.0` (`CONFLICT`)
   - `payments: 1.9.0 < 2.0.0` (`CONFLICT`)
   - `ic_diwali` missing from `native_resources.launcher_icons` (`CONFLICT`)
   - `legacy_pin_flow` enabled alongside `biometric_checkout` (`CONFLICT`)
   - Result: `total=6 pass=2 conflicts=4 unknown=0 skipped=0 blocking=True` → **Exit code `1`**.
2. **Passing release (`aurelia_ios.yaml` against `Production`):**
   - `stripe_sdk: 3.2.0`, `payments: 2.2.0`, `ic_diwali` present, `legacy_pin_flow` disabled (`SKIPPED`).
   - Result: `total=6 pass=5 conflicts=0 unknown=0 skipped=1 blocking=False` → **Exit code `0`**.

## CI/CD Integration

See [.github/workflows/flagmatrix-gate.yml](.github/workflows/flagmatrix-gate.yml). The workflow runs offline unit/regression tests (`pytest -m "not live" -v`), spins up an isolated self-hosted Flagsmith instance via Docker Compose, seeds it with `examples/seed_flagsmith.py`, verifies the blocking gate (exit `1`) and passing gate (exit `0`), and uploads JSON/Markdown reports as artifacts.

## Running FastAPI & Flutter Studio

```powershell
# Terminal 1: FastAPI adapter
.\.venv\Scripts\uvicorn.exe flagmatrix_api.app:app --host 127.0.0.1 --port 8080

# Terminal 2: Flutter Studio
cd studio
flutter run -d chrome
```

## Verified Test Results

- `pytest -m "not live" -v`: **23 passed** (core, CLI, FastAPI, fintech E2E, audit regressions).
- `pytest -m live -v`: **1 passed** (live integration against self-hosted Flagsmith `2.295.2`).
- `studio/`: `flutter analyze` (**No issues found**), `flutter test` (**1 passed**), `flutter build web` (**Built `build\web`**).
- `examples/sample_app/`: `flutter test` (**1 passed**).

## Limitations & License

- **Limitations:** `AppState` in `flagmatrix_api` stores validation history in memory (not persisted across API restarts). Self-hosted Flagsmith OSS single-project setups reuse the default project if `POST /api/v1/projects/` returns `403`.
- **License:** MIT — see [LICENSE](LICENSE).
