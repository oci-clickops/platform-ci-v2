#!/usr/bin/env python3
"""
Update Ansible state file in OCI bucket after successful execution
"""

import os
import sys
import json
from datetime import datetime
import oci
from oci.object_storage import ObjectStorageClient


def get_oci_client():
    """Initialize OCI client with instance principal"""
    try:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        return ObjectStorageClient(config={}, signer=signer)
    except Exception as e:
        print(f"Warning: Could not initialize OCI client with instance principal: {e}")
        try:
            config = oci.config.from_file()
            return ObjectStorageClient(config)
        except Exception as e2:
            print(f"Error: Could not initialize OCI client: {e2}")
            return None


def update_state(state, manifest):
    """
    Update state with operation results
    """
    state['last_updated'] = datetime.utcnow().isoformat() + 'Z'

    operation_type = manifest.get('operation_type')
    operation_version = manifest.get('operation_version', '1.0.0')
    targets = manifest.get('targets', {})

    # Update VM resources
    for vm_target in targets.get('vm_resources', []):
        logical_key = vm_target.get('logical_key')

        if logical_key not in state['resources']:
            state['resources'][logical_key] = {'operations': {}}

        # Build agent info
        agents_info = {}
        for agent in vm_target.get('agents', []):
            agent_type = agent.get('type')
            agents_info[agent_type] = {
                'version': agent.get('version'),
                'installed_at': datetime.utcnow().isoformat() + 'Z'
            }

        state['resources'][logical_key]['operations'][operation_type] = {
            'completed': datetime.utcnow().isoformat() + 'Z',
            'status': 'success',
            'version': operation_version,
            'agents': agents_info
        }

    # Update ADB resources
    for adb_target in targets.get('adb_resources', []):
        logical_key = adb_target.get('logical_key')
        action = adb_target.get('action')

        if logical_key not in state['resources']:
            state['resources'][logical_key] = {'operations': {}}

        state['resources'][logical_key]['operations'][operation_type] = {
            'completed': datetime.utcnow().isoformat() + 'Z',
            'status': 'success',
            'action': action,
            'version': operation_version
        }

    return state


def upload_state(client, namespace, bucket, state_key, state):
    """
    Upload updated state to OCI bucket
    """
    state_json = json.dumps(state, indent=2)

    client.put_object(
        namespace_name=namespace,
        bucket_name=bucket,
        object_name=state_key,
        put_object_body=state_json
    )


def main():
    if len(sys.argv) != 6:
        print("Error: Missing required arguments")
        print("Usage: ansible_update_state.py <cloud> <bucket> <state-key> <state-file> <operation-file>")
        sys.exit(1)

    cloud = sys.argv[1]
    bucket = sys.argv[2]
    state_key = sys.argv[3]
    state_file = sys.argv[4]
    operation_file = sys.argv[5]

    namespace = os.environ.get('STATE_NAMESPACE')

    if not namespace:
        print("Error: STATE_NAMESPACE environment variable not set")
        sys.exit(1)

    # Load current state and manifest
    with open(state_file, 'r') as f:
        state = json.load(f)

    with open(operation_file, 'r') as f:
        manifest = json.load(f)

    print("💾 Updating Ansible state...")

    # Update state
    updated_state = update_state(state, manifest)

    if cloud == 'oci':
        client = get_oci_client()

        if not client:
            print("Error: Could not initialize OCI client")
            sys.exit(1)

        upload_state(client, namespace, bucket, state_key, updated_state)
        print(f"✅ State updated in bucket: {state_key}")
    else:
        # Azure implementation
        print(f"Warning: {cloud} not yet implemented")

    # Also save locally for debugging
    with open('/tmp/ansible-state-updated.json', 'w') as f:
        json.dump(updated_state, f, indent=2)


if __name__ == "__main__":
    main()
