#!/usr/bin/env python3
"""
Update OCI resource tags after Ansible operation
Tracks agent versions, installation dates, etc.
"""

import os
import sys
import json
from datetime import datetime
import oci
from oci.core import ComputeClient
from oci.database import DatabaseClient


def get_oci_clients():
    """Initialize OCI clients with instance principal"""
    try:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        compute = ComputeClient(config={}, signer=signer)
        database = DatabaseClient(config={}, signer=signer)
        return compute, database
    except Exception as e:
        print(f"Warning: Could not initialize OCI clients with instance principal: {e}")
        try:
            config = oci.config.from_file()
            compute = ComputeClient(config)
            database = DatabaseClient(config)
            return compute, database
        except Exception as e2:
            print(f"Error: Could not initialize OCI clients: {e2}")
            return None, None


def update_compute_tags(compute_client, instance_ocid, tags):
    """
    Update freeform tags on compute instance
    """
    try:
        # First get current tags to merge
        instance = compute_client.get_instance(instance_id=instance_ocid).data
        current_tags = instance.freeform_tags or {}

        # Merge new tags with existing
        merged_tags = {**current_tags, **tags}

        compute_client.update_instance(
            instance_id=instance_ocid,
            update_instance_details=oci.core.models.UpdateInstanceDetails(
                freeform_tags=merged_tags
            )
        )
        print(f"✅ Updated tags on instance {instance_ocid[:20]}...")
        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not update tags on {instance_ocid}: {e}")
        return False


def update_adb_tags(database_client, adb_ocid, tags):
    """
    Update freeform tags on ADB
    """
    try:
        # First get current tags to merge
        adb = database_client.get_autonomous_database(autonomous_database_id=adb_ocid).data
        current_tags = adb.freeform_tags or {}

        # Merge new tags with existing
        merged_tags = {**current_tags, **tags}

        database_client.update_autonomous_database(
            autonomous_database_id=adb_ocid,
            update_autonomous_database_details=oci.database.models.UpdateAutonomousDatabaseDetails(
                freeform_tags=merged_tags
            )
        )
        print(f"✅ Updated tags on ADB {adb_ocid[:20]}...")
        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not update tags on {adb_ocid}: {e}")
        return False


def main():
    if len(sys.argv) != 4:
        print("Error: Missing required arguments")
        print("Usage: ansible_update_tags.py <cloud> <operation-file> <inventory-file>")
        sys.exit(1)

    cloud = sys.argv[1]
    operation_file = sys.argv[2]
    inventory_file = sys.argv[3]

    # Load files
    with open(operation_file, 'r') as f:
        manifest = json.load(f)

    with open(inventory_file, 'r') as f:
        inventory = json.load(f)

    state_tracking = manifest.get('state_tracking', {})

    if not state_tracking.get('update_tags', False):
        print("ℹ️  Tag updates disabled in manifest")
        return

    print("🏷️  Updating resource tags...")

    if cloud == 'oci':
        compute_client, database_client = get_oci_clients()

        if not compute_client or not database_client:
            print("Error: Could not initialize OCI clients")
            sys.exit(1)

        targets = manifest.get('targets', {})
        current_time = datetime.utcnow().isoformat() + 'Z'

        # Update VM tags
        vm_count = 0
        for vm_target in targets.get('vm_resources', []):
            logical_key = vm_target.get('logical_key')
            host_vars = inventory.get('_meta', {}).get('hostvars', {}).get(logical_key, {})
            ocid = host_vars.get('oci_ocid')

            if ocid:
                # Build tag dict
                tags = state_tracking.get('tags', {}).copy()

                # Add agent-specific tags
                for agent in vm_target.get('agents', []):
                    agent_type = agent.get('type')
                    agent_version = agent.get('version')
                    tags[f'{agent_type}_agent_installed'] = 'true'
                    tags[f'{agent_type}_agent_version'] = agent_version

                tags['last_ansible_run'] = current_time
                tags['ansible_operation'] = manifest.get('operation_type')

                if update_compute_tags(compute_client, ocid, tags):
                    vm_count += 1
            else:
                print(f"⚠️  Warning: No OCID found for VM {logical_key}")

        # Update ADB tags
        adb_count = 0
        for adb_target in targets.get('adb_resources', []):
            logical_key = adb_target.get('logical_key')
            host_vars = inventory.get('_meta', {}).get('hostvars', {}).get(logical_key, {})
            ocid = host_vars.get('oci_ocid')

            if ocid:
                tags = {
                    'last_ansible_run': current_time,
                    'last_action': adb_target.get('action'),
                    'ansible_operation': manifest.get('operation_type')
                }
                if update_adb_tags(database_client, ocid, tags):
                    adb_count += 1
            else:
                print(f"⚠️  Warning: No OCID found for ADB {logical_key}")

        print(f"✅ Tags updated: {vm_count} VMs + {adb_count} ADBs")
    else:
        # Azure implementation
        print(f"Warning: {cloud} not yet implemented")


if __name__ == "__main__":
    main()
