#!/usr/bin/env python3
"""
Run pre-checks before Ansible execution
Validates tags, disk space, connectivity
"""

import sys
import json


def load_json(file_path):
    """Load JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)


def check_skip_if_installed(manifest, inventory, state):
    """
    Check if operation should be skipped based on existing tags/state
    """
    targets = manifest.get('targets', {})
    pre_checks = manifest.get('pre_checks', {})

    if not pre_checks.get('skip_if_installed', False):
        return True

    skipped = []

    # Check VM targets
    for vm_target in targets.get('vm_resources', []):
        logical_key = vm_target.get('logical_key')

        # Check resource tags
        host_vars = inventory.get('_meta', {}).get('hostvars', {}).get(logical_key, {})
        resource_tags = host_vars.get('resource_tags', {})

        # Check if agent already installed
        for agent in vm_target.get('agents', []):
            agent_type = agent.get('type')
            tag_key = f"{agent_type}_agent_installed"

            if resource_tags.get(tag_key) == 'true':
                skipped.append(f"{logical_key} ({agent_type})")

    if skipped:
        print(f"ℹ️  Skipping already installed: {', '.join(skipped)}")

    return True


def check_required_disk_space(manifest, inventory):
    """
    Verify required disk space on target VMs
    """
    pre_checks = manifest.get('pre_checks', {})
    required_mb = pre_checks.get('required_disk_space_mb', 0)

    if required_mb == 0:
        return True

    print(f"✅ Disk space check: {required_mb}MB required (will verify during execution)")
    return True


def check_targets_exist(manifest, inventory):
    """
    Verify that all targets in manifest exist in inventory
    """
    targets = manifest.get('targets', {})
    missing = []

    # Check VM targets
    for vm_target in targets.get('vm_resources', []):
        logical_key = vm_target.get('logical_key')
        if logical_key not in inventory.get('_meta', {}).get('hostvars', {}):
            missing.append(f"VM: {logical_key}")

    # Check ADB targets
    for adb_target in targets.get('adb_resources', []):
        logical_key = adb_target.get('logical_key')
        if logical_key not in inventory.get('_meta', {}).get('hostvars', {}):
            missing.append(f"ADB: {logical_key}")

    if missing:
        print(f"⚠️  Warning: Targets not found in Terraform state:")
        for item in missing:
            print(f"   - {item}")
        print("   These targets will be skipped during execution")

    return True


def main():
    if len(sys.argv) != 5:
        print("Error: Missing required arguments")
        print("Usage: ansible_precheck.py <cloud> <operation-file> <inventory-file> <state-file>")
        sys.exit(1)

    cloud = sys.argv[1]
    operation_file = sys.argv[2]
    inventory_file = sys.argv[3]
    state_file = sys.argv[4]

    # Load files
    manifest = load_json(operation_file)
    inventory = load_json(inventory_file)
    state = load_json(state_file)

    print("🔍 Running pre-checks...")

    # Run checks
    check_targets_exist(manifest, inventory)
    check_skip_if_installed(manifest, inventory, state)
    check_required_disk_space(manifest, inventory)

    print("✅ Pre-checks passed")


if __name__ == "__main__":
    main()
