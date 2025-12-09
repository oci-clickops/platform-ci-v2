#!/usr/bin/env python3
"""
Replace placeholder values in configuration files
This script finds JSON files and replaces __PLACEHOLDERS__ with real values
"""

# Import libraries we need
import os      # To read environment variables and walk through folders
import sys     # To read command line arguments


def find_json_files(directory):
    """
    Find all JSON files in a directory and its subfolders

    Returns a list of file paths
    """

    json_files = []  # Empty list to store file paths

    # Walk through all folders and files
    for folder_path, folder_names, file_names in os.walk(directory):

        # Look at each file
        for file_name in file_names:

            # Check if it ends with .json
            if file_name.endswith('.json'):
                # Create the full path to the file
                full_path = os.path.join(folder_path, file_name)
                # Add it to our list
                json_files.append(full_path)

    return json_files


def replace_in_file(file_path, old_text, new_text):
    """
    Open a file, replace text, and save it back

    For example:
    Replace all "__PASSWORD__" with "secret123"
    """

    # Step 1: Read the file
    with open(file_path, 'r') as file:
        content = file.read()

    # Step 2: Replace the text
    new_content = content.replace(old_text, new_text)

    # Step 3: Write it back to the file
    with open(file_path, 'w') as file:
        file.write(new_content)


def process_oci_files(config_dir):
    """
    Replace OCI placeholders in JSON files
    """

    # Get the password from environment
    atp_password = os.environ.get("ATP_ADMIN_PASSWORD")

    # If password is not set, skip this
    if not atp_password:
        print("Warning: ATP_ADMIN_PASSWORD not set, skipping replacement")
        return

    # Find all JSON files
    json_files = find_json_files(config_dir)

    # Replace in each file
    for json_file in json_files:
        replace_in_file(json_file, "__ATP_ADMIN_PASSWORD__", atp_password)

    print(f"✅ Replaced ATP_ADMIN_PASSWORD in {len(json_files)} config files")


def process_azure_files(config_dir):
    """
    Replace Azure placeholders in JSON files
    """

    # Get the subscription ID from environment
    subscription_id = os.environ.get("ARM_SUBSCRIPTION_ID")

    # This one is required for Azure
    if not subscription_id:
        print("Error: ARM_SUBSCRIPTION_ID not set")
        sys.exit(1)

    # Find all JSON files
    json_files = find_json_files(config_dir)

    # Replace in each file
    for json_file in json_files:
        replace_in_file(json_file, "__SUBSCRIPTION_ID__", subscription_id)

    print(f"✅ Replaced SUBSCRIPTION_ID in {len(json_files)} config files")


def main():
    """
    Main function - This is where the program starts
    """

    # Step 1: Check if we got the right arguments
    if len(sys.argv) != 3:
        print("Error: Missing required arguments")
        print("Usage: python replace_placeholders.py <cloud-provider> <config-dir>")
        print("Example: python replace_placeholders.py oci /path/to/config")
        sys.exit(1)

    # Step 2: Get the arguments
    cloud_provider = sys.argv[1]  # "oci" or "azure"
    config_dir = sys.argv[2]      # Path to config folder

    # Step 3: Check if the config directory exists
    if not os.path.exists(config_dir):
        print(f"Error: Config directory does not exist: {config_dir}")
        sys.exit(1)

    # Step 4: Process based on cloud provider
    if cloud_provider == "oci":
        process_oci_files(config_dir)

    elif cloud_provider == "azure":
        process_azure_files(config_dir)

    else:
        print(f"Error: Unknown cloud provider '{cloud_provider}'")
        print("Supported providers: oci, azure")
        sys.exit(1)


# This line makes the script run when you execute it
if __name__ == "__main__":
    main()
