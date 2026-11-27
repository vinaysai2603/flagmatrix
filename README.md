# FlagMatrix

Open-source, deterministic feature configuration compatibility toolkit for self-hosted Flagsmith.

## Quickstart

### 1. Install FlagMatrix

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Run CLI Commands

```powershell
flagmatrix init --dir my-project
flagmatrix connect --url http://localhost:8000
flagmatrix validate --config examples/flagmatrix.yaml --profiles examples/profiles --rules examples/rules.yaml --env Development
flagmatrix compare --source Development --target Production --profiles examples/profiles --rules examples/rules.yaml
flagmatrix report report.json --format markdown
```

Exit codes:
- `0` — Validation passed
- `1` — Compatibility conflicts (or `UNKNOWN` in `--strict` mode) block the release
- `2` — Invalid configuration, malformed manifest/rules, or Flagsmith API error

### 3. Run FastAPI Adapter & Flutter Studio

```powershell
uvicorn flagmatrix_api.app:app --host 127.0.0.1 --port 8080
cd studio
flutter run -d chrome
```

### 4. CI/CD Release Gate

See [.github/workflows/flagmatrix-gate.yml](.github/workflows/flagmatrix-gate.yml) for a ready-to-use GitHub Actions release gate.

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration & Schema Reference](docs/configuration.md)
- [Deployment & Local Setup](deployment/README.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT — see [LICENSE](LICENSE).
