# Platform CI

Reusable GitHub Actions workflows for multi-cloud GitOps (Terraform + Ansible).

## Overview

Centralized CI/CD workflows for:

- **Terraform**: Infrastructure provisioning (OCI, Azure)
- **Ansible**: Day-2 operations (ADB lifecycle only)

## Structure

```
.github/
├── workflows/
│   ├── terraform-shared.yaml      # Terraform workflow
│   └── ansible-shared.yaml        # Ansible workflow
├── actions/
│   ├── terraform-workflow/        # Terraform composite action
│   └── ansible-workflow/          # Ansible composite action  
├── scripts_python/                # Python scripts (7 total)
│   ├── discover.py               # Discovery (terraform|ansible)
│   ├── terraform_setup.py        # Terraform backend setup
│   ├── ansible_generate_inventory.py  # Dynamic inventory
│   ├── common.py                 # Shared utilities
│   ├── config.py                 # Constants
│   ├── discovery_functions.py    # Discovery helpers
│   └── oci_cli_utils.py          # OCI CLI wrappers
└── ansible/
    ├── playbooks/master.yml      # Tag-routed playbook
    └── roles/adb-lifecycle/      # ADB start/stop operations
```

## Workflows

### Terraform Workflow

Plan and apply infrastructure changes.

**Usage** (in manifest repo):

```yaml
name: OCI Terraform GitOps
on:
  pull_request:
    paths: ['oci/**']
  push:
    branches: [main]
    paths: ['oci/**']

jobs:
  terraform:
    uses: oci-clickops/platform-ci/.github/workflows/terraform-shared.yaml@main
    with:
      cloud: oci
      orchestrator_repo: oci-clickops/clickops-terraform-oci-modules-orchestrator
      runner: self-hosted, oci
```

### Ansible Workflow

Execute day-2 operations on infrastructure.

**Usage** (in manifest repo):

```yaml
name: OCI Ansible Operations
on:
  workflow_dispatch:
    inputs:
      operation_file:
        required: true
      mode:
        type: choice
        options: [check, execute]

jobs:
  ansible:
    uses: oci-clickops/platform-ci/.github/workflows/ansible-shared.yaml@main
    with:
      operation-file: ${{ inputs.operation_file }}
      mode: ${{ inputs.mode }}
      cloud: oci
```

## Scripts

### Utilities (4)

- `common.py` - Shared functions (JSON, logging, GitHub outputs)
- `config.py` - Constants and paths
- `oci_cli_utils.py` - OCI CLI wrappers (subprocess-based)
- `discovery_functions.py` - Discovery helpers

### Executables (3)

- `discover.py` - Backend/operation discovery (terraform|ansible)
- `terraform_setup.py` - Terraform backend configuration
- `ansible_generate_inventory.py` - Dynamic inventory from Terraform state

**Total**: 7 scripts, ~1126 lines

## Authentication

- **OCI**: Instance Principal (automatic on self-hosted runners)
- **Azure**: Service Principal (configured in runner variables)

## State Management

- **Terraform State**: OCI Object Storage (`{bucket}/{cloud}/{region}/terraform.tfstate`)
- **Ansible State**: GitHub Actions logs (no separate state file)

## Requirements

### Runner Setup

- OCI CLI configured with Instance Principal
- Terraform >= 1.12.0
- Ansible >= 2.15
- Python 3.8+

### Collections

- `oracle.oci` (for Ansible OCI operations)

## License

MIT
