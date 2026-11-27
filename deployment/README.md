# Deployment & Local Setup

## 1. Self-Hosted Flagsmith

Start the local Flagsmith stack from `flagsmith/`:

```powershell
cd flagsmith
docker compose up -d
```

Verify health:

```powershell
Invoke-WebRequest http://localhost:8000/health/liveness/
```

Keep `flagsmith/flagsmith.env` out of source control (it is listed in `.gitignore`).

## 2. FlagMatrix Python Environment & FastAPI Adapter

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn flagmatrix_api.app:app --host 127.0.0.1 --port 8080
```

## 3. FlagMatrix Studio (Flutter)

```powershell
cd studio
flutter pub get
flutter run -d chrome
# or on Windows desktop:
flutter run -d windows
```
