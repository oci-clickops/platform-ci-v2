#!/usr/bin/env python3
"""
Generate dynamic Ansible inventory from Terraform state
Maps logical keys to actual resources (IPs, OCIDs)
"""

import os
import sys
import json
import oci
from oci.object_storage import ObjectStorageClient


def get_oci_client():
    """Initialize OCI client with instance principal"""
    try:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        return ObjectStorageClient(config={}, signer=signer)
    except Exception as e:
        print(f"Warning: Could not initialize OCI client with instance principal: {e}")
        print("Falling back to config file authentication")
        try:
            config = oci.config.from_file()
            return ObjectStorageClient(config)
        except Exception as e2:
            print(f"Error: Could not initialize OCI client: {e2}")
            return None


def download_terraform_state(client, namespace, bucket, config_path):
    """
    Download terraform.tfstate from OCI bucket

    Terraform stores state at: {bucket}/{cloud}/{region}/terraform.tfstate
    Example: oe-env-project-template/oci/eu-frankfurt-1/terraform.tfstate

    Note: We assume bucket name == repository name (GitHub Actions default)
    """
    try:
        # Convert ansible path to terraform state path
        # oci/eu-frankfurt-1 → oci/eu-frankfurt-1/terraform.tfstate
        # Remove 'ansible/' prefix if present (shouldn't have it, but defensive)
        tf_state_path = config_path.replace('ansible/', '')

        # Terraform state key includes bucket/repo name as prefix
        # This matches Terraform's discover_backend.py pattern:
        #   state_key = f"{repo_name}/{config_path}/terraform.tfstate"
        # Since bucket_name == repo_name in GitHub Actions, we use bucket here
        tf_state_key = f"{bucket}/{tf_state_path}/terraform.tfstate"

        print(f"   Downloading Terraform state: {tf_state_key}")

        obj = client.get_object(namespace, bucket, tf_state_key)
        state_data = json.loads(obj.data.content.decode('utf-8'))
        return state_data
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            print(f"Warning: Terraform state not found at {tf_state_key}")
            return None
        print(f"Error downloading Terraform state: {e}")
        return None
    except Exception as e:
        print(f"Error parsing Terraform state: {e}")
        return None


def parse_terraform_outputs(state_data):
    """
    Parse Terraform state to extract resource information

    Returns dict of logical_key → resource_info
    """
    resources_map = {}

    if not state_data:
        return resources_map

    # Parse resources section
    resources = state_data.get('resources', [])

    for resource in resources:
        resource_type = resource.get('type')
        resource_name = resource.get('name')
        instances = resource.get('instances', [])

        for instance in instances:
            attrs = instance.get('attributes', {})

            # Extract compute instances
            if resource_type == 'oci_core_instance':
                # Use display_name or resource name as logical key
                logical_key = attrs.get('display_name', resource_name)
                resources_map[logical_key] = {
                    'type': 'compute',
                    'ocid': attrs.get('id'),
                    'private_ip': attrs.get('private_ip'),
                    'public_ip': attrs.get('public_ip'),
                    'state': attrs.get('state'),
                    'defined_tags': attrs.get('defined_tags', {}),
                    'freeform_tags': attrs.get('freeform_tags', {})
                }

            # Extract ADB instances
            elif resource_type == 'oci_database_autonomous_database':
                logical_key = attrs.get('display_name', resource_name)
                resources_map[logical_key] = {
                    'type': 'adb',
                    'ocid': attrs.get('id'),
                    'db_name': attrs.get('db_name'),
                    'state': attrs.get('lifecycle_state'),
                    'connection_urls': attrs.get('connection_urls', {}),
                    'defined_tags': attrs.get('defined_tags', {}),
                    'freeform_tags': attrs.get('freeform_tags', {})
                }

    return resources_map


def load_operation_manifest(operation_file):
    """Load operation JSON manifest"""
    with open(operation_file, 'r') as f:
        return json.load(f)


def build_ansible_inventory(manifest, resources_map):
    """
    Build Ansible inventory from manifest + Terraform state

    Returns inventory in JSON format
    """
    inventory = {
        '_meta': {
            'hostvars': {}
        },
        'all': {
            'children': ['compute_instances', 'adb_instances']
        },
        'compute_instances': {
            'hosts': []
        },
        'adb_instances': {
            'hosts': []
        }
    }

    targets = manifest.get('targets', {})

    # Process VM targets
    vm_resources = targets.get('vm_resources', [])
    for vm_target in vm_resources:
        logical_key = vm_target.get('logical_key')

        if logical_key in resources_map:
            resource_info = resources_map[logical_key]

            # Use private IP as ansible host
            ansible_host = resource_info.get('private_ip')

            if ansible_host:
                inventory['compute_instances']['hosts'].append(logical_key)

                # Set host vars
                ssh_config = vm_target.get('ssh_config', {})
                inventory['_meta']['hostvars'][logical_key] = {
                    'ansible_host': ansible_host,
                    'ansible_user': ssh_config.get('user', 'opc'),
                    'ansible_become': ssh_config.get('become', True),
                    'ansible_become_user': ssh_config.get('become_user', 'root'),
                    'ansible_python_interpreter': '/usr/bin/python3',
                    'oci_ocid': resource_info.get('ocid'),
                    'oci_state': resource_info.get('state'),
                    'agents': vm_target.get('agents', []),
                    'resource_tags': resource_info.get('freeform_tags', {})
                }
            else:
                print(f"Warning: No private IP found for VM {logical_key}")
        else:
            print(f"Warning: VM resource {logical_key} not found in Terraform state")

    # Process ADB targets
    adb_resources = targets.get('adb_resources', [])
    for adb_target in adb_resources:
        logical_key = adb_target.get('logical_key')

        if logical_key in resources_map:
            resource_info = resources_map[logical_key]

            # ADB runs on localhost (OCI API calls)
            inventory['adb_instances']['hosts'].append(logical_key)

            inventory['_meta']['hostvars'][logical_key] = {
                'ansible_connection': 'local',
                'oci_ocid': resource_info.get('ocid'),
                'oci_state': resource_info.get('state'),
                'db_name': resource_info.get('db_name'),
                'action': adb_target.get('action'),
                'wait_for_state': adb_target.get('wait_for_state', True),
                'timeout_minutes': adb_target.get('timeout_minutes', 30),
                'resource_tags': resource_info.get('freeform_tags', {})
            }
        else:
            print(f"Warning: ADB resource {logical_key} not found in Terraform state")

    return inventory


def main():
    if len(sys.argv) != 5:
        print("Error: Missing required arguments")
        print("Usage: ansible_generate_inventory.py <cloud> <bucket> <config-path> <operation-file>")
        sys.exit(1)

    cloud = sys.argv[1]
    bucket = sys.argv[2]
    config_path = sys.argv[3]
    operation_file = sys.argv[4]

    namespace = os.environ.get('STATE_NAMESPACE')

    if not namespace:
        print("Warning: STATE_NAMESPACE environment variable not set")

    print("📋 Generating dynamic inventory...")

    resources_map = {}

    if cloud == 'oci':
        # Get OCI client
        client = get_oci_client()

        if client and namespace:
            # Download Terraform state
            state_data = download_terraform_state(client, namespace, bucket, config_path)

            # Parse resources
            resources_map = parse_terraform_outputs(state_data)

            print(f"✅ Found {len(resources_map)} resources in Terraform state")
        else:
            print("Warning: Could not load Terraform state, creating empty inventory")
    else:
        # Azure implementation
        print(f"Warning: {cloud} not yet implemented, creating empty inventory")

    # Load operation manifest
    manifest = load_operation_manifest(operation_file)

    # Build inventory
    inventory = build_ansible_inventory(manifest, resources_map)

    # Save to file
    with open('/tmp/inventory.json', 'w') as f:
        json.dump(inventory, f, indent=2)

    compute_count = len(inventory['compute_instances']['hosts'])
    adb_count = len(inventory['adb_instances']['hosts'])
    print(f"✅ Generated inventory: {compute_count} compute + {adb_count} ADB hosts")


if __name__ == "__main__":
    main()
