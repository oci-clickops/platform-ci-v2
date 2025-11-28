# Platform CI

This repository contains reusable GitHub Actions workflows for the GitOps architecture.

## Workflows

- **`oci-shared-simple.yaml`**: Reusable workflow for OCI Terraform deployments (Plan & Apply).
- **`azure-shared-simple.yaml`**: Reusable workflow for Azure Terraform deployments (Plan & Apply).

These workflows are designed to be called by other repositories (e.g., `oci-gitops-demoProject1`) to enforce a consistent CI/CD pipeline.
