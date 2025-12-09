# Operations Catalog

Catalog of available Ansible operations for APEX UI.

## Purpose

APEX reads these JSON files to:

1. Discover available operations
2. Generate dynamic UI forms
3. Know which workflow to trigger

## Structure

Each operation is defined in a simple JSON file:

```json
{
  "name": "Operation Name",
  "description": "What it does",
  "workflow": "oci-ansible-gitops.yaml",
  "auto_approve": true,
  "parameters": {
    "param_name": {
      "label": "User-friendly label",
      "type": "choice|boolean|number",
      "options": ["opt1", "opt2"],
      "required": true
    }
  }
}
```

## APEX Flow

```
1. APEX reads catalog from platform-ci/operations-catalog/
2. User selects operation and fills parameters
3. APEX generates Ansible manifest
4. APEX writes manifest to oe-env-project-template/oci/.../ansible/
5. APEX creates PR → auto-approve → merge
6. Workflow triggers and executes operation
```

## Adding Operations

1. Create new JSON file here
2. Define parameters
3. APEX auto-discovers it
4. Ready to use

**100% GitOps**: Catalog = code, Manifests = config ✅
