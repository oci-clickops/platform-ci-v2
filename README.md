# Platform CI

Shared GitOps workflows for multi-cloud infrastructure (OCI + Azure).

## Quick Start

```yaml
# In your project repo
jobs:
  terraform:
    uses: oci-clickops/platform-ci/.github/workflows/terraform-shared.yaml@main
    with:
      mode: ${{ github.event_name == 'pull_request' && 'pr' || 'apply' }}
      cloud: oci
      region: eu-frankfurt-1
      orchestrator_repo: oci-clickops/clickops-terraform-oci-modules-orchestrator
      bucket_name: clickops-common-bucket
      # runner_labels: '["self-hosted","oci"]'
```

## Structure

```
.github/workflows/
├── terraform-shared.yaml    # Terraform plan/apply
└── ansible-shared.yaml      # Ansible check/execute

scripts_python/
├── utils.py                 # OCI bucket utilities
└── ansible_inventory.py     # Dynamic inventory from Terraform state

ansible/
├── ansible.cfg
├── requirements.yml
└── playbooks/
    ├── master.yml           # Operation router (tags)
    ├── common/send-notification.yml
    └── operations/adb-lifecycle.yml
```

## Workflows

| Workflow | Inputs | Purpose |
|----------|--------|---------|
| `terraform-shared` | mode, cloud, orchestrator_repo, bucket_name | Terraform GitOps |
| `ansible-shared` | mode, cloud, operation_file, bucket_name | Ansible Day-2 ops |

## Caller Repo Layout (Expected)

These workflows are designed to be called from a “manifest” repo that contains per-cloud/per-region config.

```
<your-repo>/
├── oci/
│   └── eu-frankfurt-1/
│       ├── *.json                 # Terraform var-files (JSON)
│       └── ansible/
│           └── adb-lifecycle.json # Operation manifest(s)
└── azure/
    └── westeurope/
        └── *.json                 # Terraform var-files (JSON)
```

## Terraform Workflow (`terraform-shared.yaml`)

**Inputs**

- `mode`: `pr` (plan + PR comment) or `apply` (apply)
- `cloud`: `oci` or `azure`
- `region`: (Optional) Config folder name (e.g., `eu-frankfurt-1`). **If omitted**, the workflow automatically detects it by checking which files changed in the `{cloud}/` directory.
- `orchestrator_repo`: repo containing the Terraform modules/orchestrator (checked out into `ORCH/`)
- `bucket_name`: OCI Object Storage bucket name used for the Terraform backend
- `runner_labels` (optional): JSON array for `runs-on` (default: `["self-hosted","oci"]`)

**Config resolution**

The workflow determines the configuration directory in this order:

1. Input `region` (if provided)
2. **Auto-detection**: Checks `git diff` for changes in `${cloud}/<region>/...`
3. Runner `REGION` env var

It then resolves to `${cloud}/${region}` (e.g., `oci/eu-frankfurt-1`) and passes all `*.json` files found there to Terraform.

**Terraform state object name**

The backend `key` (and the Ansible inventory downloader) uses:

`<bucket_name>/<github.repository>/<cloud>/<region>/terraform.tfstate`

## Ansible Workflow (`ansible-shared.yaml`)

Runs Day-2 operations using Ansible, driven by a JSON “operation manifest”.

**Inputs**

- `mode`: `check` or `execute`
- `cloud`: currently only `oci` is supported end-to-end (inventory generation rejects `azure`)
- `operation_file` (optional): path to the operation JSON; if omitted, it is auto-detected from the git diff
- `bucket_name`: OCI Object Storage bucket used to download Terraform state
- `runner_labels` (optional): JSON array for `runs-on` (default: `["self-hosted","oci"]`)

**Operation auto-detection**

When `operation_file` is empty, the workflow picks the first changed file matching:

- path contains `${cloud}`
- path contains `ansible`
- filename ends with `.json`

Recommended location: `${cloud}/${region}/ansible/<operation>.json`.

**Operation JSON format**

`operation_type` must match the Ansible tag in `ansible/playbooks/master.yml` (e.g., `adb-lifecycle`).

```json
{
  "operation_type": "adb-lifecycle",
  "targets": [
    { "display_name": "my-adb", "action": "stop", "wait_for_state": true, "timeout_minutes": 30 }
  ]
}
```

Targets are matched against ADB `display_name` values found in Terraform state (`oci_database_autonomous_database` resources).

## Authentication

- **OCI**: Instance Principal (self-hosted runners)
- **Azure**: Service Principal (env vars)

### OCI Credentials File (for IAM resources)

If your project needs to create **IAM resources** (compartments, groups, policies), you must include an `oci-credentials.tfvars.json` file in your config directory with the real `tenancy_ocid`. This follows the same pattern as `oci-clickops-lz`.

```json
{
    "tenancy_ocid": "ocid1.tenancy.oc1..YOUR_TENANCY_OCID",
    "user_ocid": "not-used-with-instance-principal",
    "fingerprint": "not-used-with-instance-principal",
    "private_key_path": "not-used-with-instance-principal",
    "private_key_password": ""
}
```

**When is this file needed?**

| Resource Type | `oci-credentials.tfvars.json` |
|---------------|-------------------------------|
| ADBs, VMs, Networks, Storage | ❌ Not required (Instance Principal handles it) |
| Compartments, Groups, Policies | ✅ **Required** (needs real `tenancy_ocid`) |

> [!IMPORTANT]
> If you only deploy databases, compute, or networking resources, you don't need this file. Add it only when creating IAM resources.

## Requirements

- Linux self-hosted runner (bash + GNU utils)
- Terraform >= 1.12.0
- Python 3.11+ (Ansible workflow installs Ansible via pip)
- Azure CLI available on the runner when `cloud: azure` is used (`az login` is invoked)
- OCI Instance Principal available on the runner (both workflows)

## Regions

- `STATE_REGION` is the **OCI region where the Terraform state bucket lives** (used by both OCI and Azure jobs because the backend is OCI Object Storage).
- Config selection uses `oci/<region>/...` or `azure/<region>/...` and is controlled by the workflow input `region` (recommended) or runner env `REGION` as a fallback.

> [!NOTE]
> **Future Improvement:** Currently `STATE_REGION` must be configured on the runner. For single-region setups (where the state bucket lives in the same region as resources), this could be simplified by defaulting to `CONFIG_REGION` when `STATE_REGION` is not set.

## Environment Variables [WORKAROUND]

These must be configured on the self-hosted runner:

| Variable | Description | Cloud | Sensitive |
|----------|-------------|-------|-----------|
| `STATE_NAMESPACE` | OCI Object Storage namespace | OCI | No |
| `STATE_REGION` | OCI region where the state bucket lives (required) | OCI/Azure | No |
| `REGION` | Config region folder name (used if workflow input `region` is omitted) | OCI/Azure | No |
| `OCI_CLI_AUTH` | Set to `instance_principal` (needed for `oci os object get` in inventory generation) | OCI | No |
| `ARM_CLIENT_ID` | Service Principal client ID | Azure | Yes |
| `ARM_CLIENT_SECRET` | Service Principal secret | Azure | Yes |
| `ARM_TENANT_ID` | Azure tenant ID | Azure | No |
| `ARM_SUBSCRIPTION_ID` | Azure subscription ID | Azure | No |

### Runner Configuration

Configure variables in the Systemd service file (`/etc/systemd/system/actions.runner...service`):

```ini
[Service]
# OCI
Environment="OCI_CLI_AUTH=instance_principal"
Environment="STATE_NAMESPACE=..."
Environment="STATE_REGION=eu-frankfurt-1"
Environment="REGION=eu-frankfurt-1"  # optional if workflows pass `region`

# Azure
Environment="ARM_SUBSCRIPTION_ID=..."
Environment="ARM_CLIENT_ID=..."
Environment="ARM_CLIENT_SECRET=..."
Environment="ARM_TENANT_ID=..."
```

Then reload: `systemctl daemon-reload && systemctl restart actions-runner...`

> **Note**: This is more secure than a `.env` file as it is owned by root.

## Scalability

Designed for multiple projects without bottlenecks:

- **Concurrency**: Each project has its own queue (scoped by `github.repository`)
  - Project A running Terraform does NOT block Project B
  - Only same-project operations serialize (prevents state conflicts)
  
- **Runner Capacity**: Add more runners to handle concurrent load
