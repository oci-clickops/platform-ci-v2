#!/usr/bin/env python3
"""
Discover Ansible operation configuration
Parses the operation manifest and sets up environment variables
"""

import os
import sys
import json


def find_operation_folder(cloud, operation_file):
    """
    Extract the region folder path from operation file

    Example:
    oci/eu-frankfurt-1/operations/adb-ops.json
    → returns "oci/eu-frankfurt-1"
    """
    # Split path and find the region
    parts = operation_file.split('/')

    # Find cloud index
    try:
        cloud_idx = parts.index(cloud)
    except ValueError:
        print(f"Error: Cloud '{cloud}' not found in operation file path")
        sys.exit(1)

    # Path is {cloud}/{region}
    if len(parts) < cloud_idx + 2:
        print(f"Error: Invalid path structure, expected {cloud}/{{region}}/...")
        sys.exit(1)

    region_path = '/'.join(parts[:cloud_idx + 2])

    return region_path


def get_region_name(config_path):
    """
    Extract region name from path

    Example: oci/eu-frankfurt-1 → eu-frankfurt-1
    """
    return os.path.basename(config_path)


def load_operation_manifest(operation_file):
    """
    Load and parse the operation JSON manifest
    """
    try:
        with open(operation_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Operation file not found: {operation_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in operation file: {e}")
        sys.exit(1)


def build_state_key(repo_name, config_path, operation_type):
    """
    Build state file key for Ansible state in OCI Object Storage

    Format: {bucket-name}/ansible/{cloud}/{region}/ansible-state-{operation}.json
    Example: oe-env-project-template/ansible/oci/eu-frankfurt-1/ansible-state-adb-lifecycle.json

    Note: repo_name parameter is actually bucket_name from GitHub Actions workflow
          (bucket_name = github.event.repository.name)

    The state key includes the bucket/repo name as an organizational prefix within
    the object path. This follows the same pattern as Terraform state files and
    allows multiple projects to share a bucket if needed.

    Ansible state is stored separately from Terraform state:
    - Terraform: {bucket}/oci/eu-frankfurt-1/terraform.tfstate
    - Ansible:   {bucket}/ansible/oci/eu-frankfurt-1/ansible-state-{operation}.json
    """
    return f"{repo_name}/ansible/{config_path}/ansible-state-{operation_type}.json"


def write_github_output(key, value):
    """Write variable to GitHub Actions output"""
    github_output_file = os.environ.get("GITHUB_OUTPUT")
    if github_output_file:
        with open(github_output_file, 'a') as f:
            f.write(f"{key}={value}\n")


def write_github_env(key, value):
    """Write variable to GitHub Actions environment"""
    github_env_file = os.environ.get("GITHUB_ENV")
    if github_env_file:
        with open(github_env_file, 'a') as f:
            f.write(f"{key}={value}\n")


def main():
    if len(sys.argv) != 4:
        print("Error: Missing required arguments")
        print("Usage: ansible_discover_operation.py <cloud> <operation-file> <bucket-name>")
        sys.exit(1)

    cloud = sys.argv[1]
    operation_file = sys.argv[2]
    bucket_name = sys.argv[3]

    print(f"🔍 Discovering operation configuration...")
    print(f"   Cloud: {cloud}")
    print(f"   Operation file: {operation_file}")

    # Parse operation manifest
    manifest = load_operation_manifest(operation_file)
    operation_type = manifest.get('operation_type')

    if not operation_type:
        print("Error: 'operation_type' not found in manifest")
        sys.exit(1)

    # Find configuration path
    config_path = find_operation_folder(cloud, operation_file)
    region = get_region_name(config_path)

    # Build state key
    state_key = build_state_key(bucket_name, config_path, operation_type)

    # Count targets
    targets = manifest.get('targets', {})
    target_count = 0
    for key, value in targets.items():
        if isinstance(value, list):
            target_count += len(value)

    # Write outputs
    write_github_output("config_subpath", config_path)
    write_github_output("region", region)
    write_github_output("operation_type", operation_type)
    write_github_output("state_key", state_key)
    write_github_output("target_count", str(target_count))

    # Write environment variables
    write_github_env("CONFIG_SUBPATH", config_path)
    write_github_env("DETECTED_REGION", region)
    write_github_env("OPERATION_TYPE", operation_type)
    write_github_env("STATE_KEY", state_key)

    print("✅ Operation discovery complete:")
    print(f"   Type: {operation_type}")
    print(f"   Path: {config_path}")
    print(f"   Region: {region}")
    print(f"   Targets: {target_count}")
    print(f"   State: {state_key}")


if __name__ == "__main__":
    main()
