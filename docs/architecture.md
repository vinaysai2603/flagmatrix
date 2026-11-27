# FlagMatrix Architecture

FlagMatrix is structured as a layered, deterministic compatibility toolkit:

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
|  - Semver Comparator (packaging.version)              |
|  - Deterministic CompatibilityEngine                  |
|  - ConfigurationTestingEngine (Flagsmith + Pairwise)  |
|  - FlagsmithClient (REST API + Official Flagsmith SDK)|
+-------------------------------------------------------+
            |
            v
+-------------------------------------------------------+
|           Self-Hosted Flagsmith Instance              |
+-------------------------------------------------------+
```

## Design Principles

1. **Zero Rule Duplication:** All compatibility checks execute in `flagmatrix_core`. Neither `flagmatrix_api` nor `studio/` duplicates rule logic.
2. **Deterministic Evaluation:** No LLMs or heuristics. Every rule returns `PASS`, `CONFLICT`, `UNKNOWN`, or `SKIPPED`.
3. **Explicit Undeclared Capabilities:** Missing capabilities in an `ApplicationProfile` are reported as `UNKNOWN`, never assumed available.
4. **Disabled Flag Safety:** Disabled flags return `SKIPPED` unless `require_enabled: true` is explicitly set.
5. **Secret Hygiene:** API keys are read from environment variables or in-memory session state and redacted via `redact_secret()` in logs and connection responses.
