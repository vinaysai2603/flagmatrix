# Contributing to FlagMatrix

Thank you for contributing to FlagMatrix!

## Development Setup

1. Create a Python 3.11+ virtual environment and install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```
2. Run Python tests:
   ```powershell
   pytest
   ```
3. Run Flutter Studio checks:
   ```powershell
   cd studio
   flutter analyze
   flutter test
   ```

## Guidelines

- Keep `core/flagmatrix_core` independent of FastAPI and Flutter.
- Do not introduce non-deterministic or LLM-based logic into the compatibility engine.
- Never commit API keys, tokens, or proprietary client data.
- All contributions are licensed under the MIT License ([LICENSE](LICENSE)).
