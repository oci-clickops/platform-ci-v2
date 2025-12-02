# Python Scripts

Helper scripts for complex workflow logic.

| Script | Description | Usage |
|--------|-------------|-------|
| `discover_backend.py` | Detects region & configures backend. | `python3 discover_backend.py <cloud>` |
| `setup_backend.py` | Generates `providers.tf`. | `python3 setup_backend.py <cloud> <path>` |
| `replace_placeholders.py` | Replaces placeholders in JSON. | `python3 replace_placeholders.py <cloud> <path>` |
| `sanitize_plan.py` | Sanitizes Terraform output. | `python3 sanitize_plan.py <cloud> "text"` |
| `test_scripts.py` | Runs unit tests. | `python3 test_scripts.py` |
