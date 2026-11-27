# Configuration & Schema Reference

## 1. `flagmatrix.yaml` (CLI Config)

```yaml
schema_version: "1.0"
flagsmith:
  url: http://localhost:8000
  api_key_env: FLAGSMITH_API_KEY_localhost_8000
project_id: 1
environment: Development
profiles_path: profiles
rules_path: rules.yaml
strict: false
```

## 2. Application Capability Manifest (`schema_version: "1.0"`)

```yaml
schema_version: "1.0"
app_id: com.novapay.wallet
tenant_id: novapay
platform: android # android | ios | web | windows | macos | linux
app_version: "3.1.0"
build_flavor: production
environment: Production
installed_sdks:
  - stripe_sdk
sdk_versions:
  stripe_sdk: "3.0.0"
native_resources:
  launcher_icons:
    - ic_launcher
    - ic_diwali
backend_api_versions:
  payments: "2.0.0"
device_capabilities:
  biometrics: true
identity_traits:
  tenant_id: novapay
```

## 3. Feature Requirement Rules (`schema_version: "1.0"`)

Supported constraint types:
- `sdk_installed`
- `sdk_version` (`min_version`, `max_version`, `equals`, `in_values`)
- `backend_api_version`
- `native_resource`
- `device_capability`
- `app_version`
- `flag_value`
- `platform_in`
- `incompatible_with`

## 4. CLI Exit Codes

- `0`: Validation passed (no conflicts, and no unknowns when `--strict` is set).
- `1`: Compatibility conflicts (or unknowns in `--strict` mode) block the release.
- `2`: Invalid configuration, malformed manifest/rules, or Flagsmith connection error.
