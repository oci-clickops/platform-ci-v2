#!/usr/bin/env python3
"""
Load existing Ansible state from OCI bucket
Tracks completed operations per resource
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
        try:
            config = oci.config.from_file()
            return ObjectStorageClient(config)
        except Exception as e2:
            print(f"Error: Could not initialize OCI client: {e2}")
            return None


def load_ansible_state(client, namespace, bucket, state_key):
    """
    Load ansible-state.json from OCI bucket

    Returns existing state or empty state structure
    """
    try:
        obj = client.get_object(namespace, bucket, state_key)
        state_data = json.loads(obj.data.content.decode('utf-8'))
        print(f"✅ Loaded existing state from {state_key}")
        return state_data
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            print(f"ℹ️  No existing state found at {state_key}, creating new state")
            return {
                "version": "1.0.0",
                "last_updated": None,
                "resources": {}
            }
        print(f"Error loading state: {e}")
        raise
    except Exception as e:
        print(f"Error parsing state: {e}")
        raise


def main():
    if len(sys.argv) != 4:
        print("Error: Missing required arguments")
        print("Usage: ansible_load_state.py <cloud> <bucket> <state-key>")
        sys.exit(1)

    cloud = sys.argv[1]
    bucket = sys.argv[2]
    state_key = sys.argv[3]

    namespace = os.environ.get('STATE_NAMESPACE')

    if not namespace:
        print("Error: STATE_NAMESPACE environment variable not set")
        sys.exit(1)

    print("📂 Loading Ansible state...")

    if cloud == 'oci':
        client = get_oci_client()

        if not client:
            print("Error: Could not initialize OCI client")
            sys.exit(1)

        state = load_ansible_state(client, namespace, bucket, state_key)
    else:
        # Azure implementation
        print(f"Warning: {cloud} not yet implemented, creating empty state")
        state = {"version": "1.0.0", "resources": {}}

    # Save to temp file for Ansible to use
    with open('/tmp/ansible-state.json', 'w') as f:
        json.dump(state, f, indent=2)

    resource_count = len(state.get('resources', {}))
    print(f"✅ State loaded: {resource_count} resources tracked")


if __name__ == "__main__":
    main()
