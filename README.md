# Platform CI

Shared GitOps workflows for multi-cloud infrastructure (OCI + Azure).

## Quick Start

```yaml
# In your project repo
jobs:
  terraform:
    uses: oci-clickops/platform-ci-v2/.github/workflows/terraform-shared.yaml@main
    with:
      mode: ${{ github.event_name == 'pull_request' && 'pr' || 'apply' }}
      cloud: oci
      orchestrator_repo: oci-clickops/clickops-terraform-oci-modules-orchestrator
      bucket_name: clickops-common-bucket
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
└── playbooks/master.yml     # ADB lifecycle operations

operations-catalog/          # APEX UI catalog
├── adb-lifecycle.json
└── deploy-agent.json
```

## Workflows

| Workflow | Inputs | Purpose |
|----------|--------|---------|
| `terraform-shared` | mode, cloud, orchestrator_repo, bucket_name | Terraform GitOps |
| `ansible-shared` | mode, cloud, operation_file, bucket_name | Ansible Day-2 ops |

## Authentication

- **OCI**: Instance Principal (self-hosted runners)
- **Azure**: Service Principal (env vars)

## Requirements

- Self-hosted runner with OCI CLI
- Terraform >= 1.12.0
- Python 3.11+

## Environment Variables

These must be configured on the self-hosted runner:

| Variable | Description | Cloud | Sensitive |
|----------|-------------|-------|-----------|
| `STATE_NAMESPACE` | OCI Object Storage namespace | OCI | No |
| `OCI_CLI_AUTH` | Set to `instance_principal` | OCI | No |
| `TF_VAR_TENANCY_ID` | OCI tenancy OCID | OCI | No |
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
Environment="TF_VAR_TENANCY_ID=ocid1.tenancy.oc1..aaa..."
Environment="STATE_NAMESPACE=..."

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
