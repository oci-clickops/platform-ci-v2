#!/usr/bin/env python3
"""
Discover backend configuration
Finds the region folder and sets up all the variables we need
"""

import os
import sys
import glob


def find_region_folder(cloud):
    """
    Find the first folder under the cloud directory

    For example:
    - oci/eu-frankfurt-1 → returns "oci/eu-frankfurt-1"
    - azure/fra → returns "azure/fra"
    """

    # Look for folders under the cloud directory
    # Pattern: oci/* or azure/*
    pattern = os.path.join(cloud, "*")
    folders = glob.glob(pattern)

    # Keep only directories (not files)
    folders = [f for f in folders if os.path.isdir(f)]

    # Return the first one we find
    if folders:
        return folders[0]
    else:
        return None


def get_region_name(config_path):
    """
    Get just the region name from the full path

    Example:
    - oci/eu-frankfurt-1 → eu-frankfurt-1
    - azure/fra → fra
    """
    return os.path.basename(config_path)


def build_state_key(repo_name, config_path):
    """
    Build the Terraform state file key

    Format: repo-name/cloud/region/terraform.tfstate
    Example: my-project/oci/eu-frankfurt-1/terraform.tfstate
    """
    return f"{repo_name}/{config_path}/terraform.tfstate"


def write_github_output(key, value):
    """
    Write a variable to GitHub Actions output
    This makes the variable available to other steps
    """

    github_output_file = os.environ.get("GITHUB_OUTPUT")

    if github_output_file:
        with open(github_output_file, 'a') as f:
            f.write(f"{key}={value}\n")


def write_github_env(key, value):
    """
    Write a variable to GitHub Actions environment
    This makes the variable available as $VAR_NAME in bash
    """

    github_env_file = os.environ.get("GITHUB_ENV")

    if github_env_file:
        with open(github_env_file, 'a') as f:
            f.write(f"{key}={value}\n")


def main():
    """
    Main function - discover backend config and set variables
    """

    # Step 1: Get arguments from command line
    if len(sys.argv) != 3:
        print("Error: Cloud provider and bucket name required")
        print("Usage: python discover_backend.py <oci|azure> <bucket-name>")
        sys.exit(1)

    cloud = sys.argv[1]
    bucket_name = sys.argv[2]

    # Step 2: Find the region folder
    config_path = find_region_folder(cloud)

    if not config_path:
        print(f"❌ Error: No region folder found under {cloud}/")
        print(f"Expected structure: {cloud}/region-name/")
        sys.exit(1)

    # Step 3: Extract region name
    region = get_region_name(config_path)

    # Step 4: Build state key
    state_key = build_state_key(bucket_name, config_path)

    # Step 5: Write outputs (for other steps to use)
    write_github_output("config_subpath", config_path)
    write_github_output("region", region)
    write_github_output("bucket_name", bucket_name)
    write_github_output("state_key", state_key)

    # Step 6: Write environment variables (for bash steps)
    write_github_env("CONFIG_SUBPATH", config_path)
    write_github_env("DETECTED_REGION", region)
    write_github_env("BUCKET_NAME", bucket_name)
    write_github_env("STATE_KEY", state_key)

    # Step 7: Show what we found
    print("✅ Backend config ready:")
    print(f"   Path: {config_path}")
    print(f"   Bucket: {bucket_name}")
    print(f"   Region: {region}")
    print(f"   State: {state_key}")


if __name__ == "__main__":
    main()
