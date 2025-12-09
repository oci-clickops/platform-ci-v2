# Platform CI

Reusable GitHub Actions workflows for multi-cloud Terraform deployments in GitOps architecture.

## Workflows

- **`terraform-shared.yaml`** - Unified Terraform Workflow (Plan & Apply) for OCI and Azure.

## Structure

```
.github/
├── workflows/
│   └── terraform-shared.yaml  # Main reusable workflow
├── actions/
│   └── terraform-workflow/    # Single composite action (all Terraform steps)
└── scripts_python/            # Python scripts (only custom logic)
    ├── discover_backend.py
    ├── setup_backend.py
    ├── replace_placeholders.py
    └── sanitize_plan.py
```

## Usage

### OCI Example

Place in `.github/workflows/oci-terraform.yaml`:

```yaml
name: OCI Terraform GitOps

on:
  pull_request:
    branches: [main]
    paths: ['oci/**']
  pull_request_target:
    types: [closed]
    branches: [main]
    paths: ['oci/**']

jobs:
  oci-terraform:
    uses: oci-clickops/platform-ci/.github/workflows/terraform-shared.yaml@main
    with:
      mode: pr
      cloud: oci
      orchestrator_repo: oci-clickops/clickops-terraform-oci-modules-orchestrator
      runner: self-hosted, oci
```

### Azure Example

Place in `.github/workflows/azure-terraform.yaml`:

```yaml
name: Azure Terraform GitOps

on:
  pull_request:
    branches: [main]
    paths: ['azure/**']
  pull_request_target:
    types: [closed]
    branches: [main]
    paths: ['azure/**']

jobs:
  azure-terraform:
    uses: oci-clickops/platform-ci/.github/workflows/terraform-shared.yaml@main
    with:
      mode: pr
      cloud: azure
      orchestrator_repo: oci-clickops/clickops-orchestrator-azure
      runner: self-hosted, oci # TODO: Change to azure runner when available
```

### Repository Structure

```
your-repo/
├── .github/workflows/deploy.yaml
└── oci/                    # or azure/
    └── eu-frankfurt-1/     # Region (auto-discovered)
        ├── network.json
        └── compute.json
```

### Required Environment Variables

These must be available on the self-hosted runner:

| Variable | Description | Scope | Location | Sensitive |
| :--- | :--- | :--- | :--- | :--- |
| `BUCKET_NAME` | OCI bucket for Terraform state | Common | Runner Env | No |
| `STATE_NAMESPACE` | OCI Object Storage namespace | Common | Runner Env | No |
| `DETECTED_REGION` | OCI region | Common | Runner Env | No |
| `ATP_ADMIN_PASSWORD` | Database admin password (optional) | OCI | Secrets | **Yes** |
| `ARM_CLIENT_ID` | Service Principal client ID | Azure | Secrets | **Yes** |
| `ARM_CLIENT_SECRET` | Service Principal secret | Azure | Secrets | **Yes** |
| `ARM_TENANT_ID` | Azure tenant ID | Azure | Runner Env | No |
| `ARM_SUBSCRIPTION_ID` | Azure subscription ID | Azure | Runner Env | No |

- **OCI:** Uses self-hosted runner with instance principals.
- **Azure:** Uses temporary Service Principal until Managed Identity is available.

> [!TIP]
> **Zero-Config Strategy:** To avoid manual configuration in every repository (and bypass Free Plan limitations), configure these variables directly in the **Systemd Service** of your Self-Hosted Runner.
>
> 1. Edit the service file (e.g., `/etc/systemd/system/actions.runner...service`).
> 2. Add the variables under `[Service]`:
>
>     ```ini
>     [Service]
>     # OCI
>     Environment="OCI_CLI_AUTH=instance_principal"
>     Environment="TF_VAR_TENANCY_ID=ocid1.tenancy.oc1..aaa..."
>     Environment="STATE_NAMESPACE=..."
>     Environment="ATP_ADMIN_PASSWORD=..."
>
>     # Azure (Temporary)
>     Environment="ARM_SUBSCRIPTION_ID=..."
>     Environment="ARM_CLIENT_ID=..."
>     Environment="ARM_CLIENT_SECRET=..."
>     Environment="ARM_TENANT_ID=..."
>     ```
>
> 3. Reload and restart: `systemctl daemon-reload && systemctl restart actions-runner...`
>
> This is more secure than a `.env` file as it is owned by root.
>
> **Note for Azure:** This is a **temporary workaround**. Once we have a dedicated Azure Runner, we will switch to **Managed Identity** and remove these secrets.

## Scalability & Concurrency

This architecture is designed to scale to hundreds of projects without bottlenecks.

- **Workflow Concurrency:** The `concurrency` group in the shared workflow is **scoped to the caller repository**.
  - *Project A* running Terraform will **NOT** block *Project B*.
  - They run completely in parallel.
  - Blocking only happens within the same project (e.g., two PRs in *Project A* trying to apply to OCI simultaneously).

- **Runner Capacity:** The only limit is your Self-Hosted Runner capacity.
  - If you have 20 projects triggering builds at the exact same second, they will queue up if you only have 1 runner.
  - **Solution:** Simply add more runners to the pool to handle the load.

## Features

- Multi-cloud (OCI, Azure)
- Hybrid backend (Azure resources + OCI state)
- Auto-sanitization of sensitive data
- PR-based plan + auto-apply on merge
- Auto-discovery of region/config
