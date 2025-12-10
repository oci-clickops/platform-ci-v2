#!/usr/bin/env python3
"""
Generar inventario dinámico de Ansible desde Terraform state.
Uso: python3 ansible_inventory.py <cloud> <bucket> <config-path> <operation-file>
"""

import os
import sys
import json
from utils import load_json, save_json, get_inventory_path, get_terraform_state_key, download_from_bucket


def download_terraform_state(namespace, bucket, config_path):
    """Descargar terraform.tfstate desde OCI bucket."""
    state_key = get_terraform_state_key(bucket, config_path)

    print(f"Cargando Terraform state...")
    print(f"   Bucket: {bucket}")
    print(f"   Key: {state_key}")

    content = download_from_bucket(namespace, bucket, state_key)

    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ JSON inválido en Terraform state: {e}")
            return None
    return None


def parse_adb_resources(state_data):
    """Extraer ADBs del Terraform state. Retorna dict display_name → info."""
    adb_map = {}

    if not state_data:
        return adb_map

    for resource in state_data.get('resources', []):
        if resource.get('type') != 'oci_database_autonomous_database':
            continue

        for instance in resource.get('instances', []):
            attrs = instance.get('attributes', {})
            display_name = attrs.get('display_name', resource.get('name'))

            adb_map[display_name] = {
                'ocid': attrs.get('id'),
                'db_name': attrs.get('db_name'),
                'state': attrs.get('lifecycle_state'),
                'freeform_tags': attrs.get('freeform_tags', {})
            }

    return adb_map


def build_inventory(manifest, adb_map):
    """Construir inventario Ansible para recursos ADB."""
    inventory = {
        '_meta': {'hostvars': {}},
        'all': {'children': {'adb_instances': {}}},
        'adb_instances': {'hosts': {}}
    }

    # targets is a list of ADB operations
    adb_resources = manifest.get('targets', [])

    for adb_target in adb_resources:
        name = adb_target.get('display_name')

        if name not in adb_map:
            print(f"\n❌ ERROR: No se encontró '{name}' en Terraform state")
            print(f"Disponibles: {list(adb_map.keys()) or '(ninguno)'}")
            sys.exit(1)

        adb_info = adb_map[name]
        inventory['adb_instances']['hosts'][name] = {}
        inventory['_meta']['hostvars'][name] = {
            'ansible_connection': 'local',
            'oci_ocid': adb_info['ocid'],
            'oci_state': adb_info['state'],
            'db_name': adb_info['db_name'],
            'action': adb_target.get('action'),
            'wait_for_state': adb_target.get('wait_for_state', True),
            'timeout_minutes': adb_target.get('timeout_minutes', 30),
        }

    return inventory


def main():
    if len(sys.argv) != 5:
        print("Uso: ansible_inventory.py <cloud> <bucket> <config-path> <operation-file>")
        sys.exit(1)

    cloud, bucket, config_path, operation_file = sys.argv[1:5]

    namespace = os.environ.get('STATE_NAMESPACE')
    if not namespace:
        print("❌ Variable STATE_NAMESPACE no configurada")
        sys.exit(1)

    if cloud != 'oci':
        print(f"❌ {cloud} no soportado")
        sys.exit(1)

    # Descargar y parsear state
    state_data = download_terraform_state(namespace, bucket, config_path)
    adb_map = parse_adb_resources(state_data)
    print(f"✅ Encontrados {len(adb_map)} ADBs en Terraform state")

    # Construir y guardar inventario
    manifest = load_json(operation_file)
    inventory = build_inventory(manifest, adb_map)

    inventory_path = get_inventory_path()
    save_json(inventory_path, inventory)

    print(f"✅ Inventario: {len(inventory['adb_instances']['hosts'])} hosts → {inventory_path}")


if __name__ == "__main__":
    main()
