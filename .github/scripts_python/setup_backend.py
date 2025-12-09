#!/usr/bin/env python3
"""
Setup Terraform backend configuration
This script creates the providers.tf file for OCI or Azure
"""

# Import libraries we need
import os      # To read environment variables and work with files
import sys     # To read command line arguments and exit with errors


def check_environment_variables():
    """
    Make sure all required environment variables are set
    Returns True if everything is OK, False if something is missing
    """

    # List of variables we need
    required_vars = ["BUCKET_NAME", "STATE_KEY", "STATE_NAMESPACE", "DETECTED_REGION"]

    # Check each one
    for var_name in required_vars:
        # Get the value from environment
        value = os.environ.get(var_name)

        # If it's empty or doesn't exist, that's a problem
        if not value:
            print(f"Error: Required environment variable {var_name} is not set")
            return False

    # If we get here, everything is OK
    return True


def get_oci_template():
    """
    Returns the Terraform configuration for OCI
    This is just a big string with the configuration
    """

    template = """provider "oci" {
  auth                = "InstancePrincipal"
  region              = var.region
  ignore_defined_tags = ["Oracle-Tags.CreatedBy", "Oracle-Tags.CreatedOn"]
}

provider "oci" {
  auth                = "InstancePrincipal"
  alias               = "home"
  region              = var.region
  ignore_defined_tags = ["Oracle-Tags.CreatedBy", "Oracle-Tags.CreatedOn"]
}

provider "oci" {
  auth                = "InstancePrincipal"
  alias               = "secondary_region"
  region              = var.region
  ignore_defined_tags = ["Oracle-Tags.CreatedBy", "Oracle-Tags.CreatedOn"]
}

terraform {
  required_version = ">= 1.12.0"
  required_providers {
    oci = {
      source                = "oracle/oci"
      configuration_aliases = [oci.home]
    }
  }
  backend "oci" {
    bucket    = "__BUCKET__"
    key       = "__KEY__"
    namespace = "__NAMESPACE__"
    auth      = "InstancePrincipal"
    region    = "__REGION__"
  }
}
"""
    return template


def get_azure_template():
    """
    Returns the Terraform configuration for Azure
    This is just a big string with the configuration
    """

    template = """provider "azurerm" {
  features {}
}

terraform {
  required_version = ">= 1.12.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  backend "oci" {
    bucket    = "__BUCKET__"
    key       = "__KEY__"
    namespace = "__NAMESPACE__"
    auth      = "InstancePrincipal"
    region    = "__REGION__"
  }
}
"""
    return template


def replace_placeholders(text):
    """
    Replace __PLACEHOLDER__ with actual values from environment variables

    For example:
    __BUCKET__ becomes the value of BUCKET_NAME
    """

    # Get values from environment
    bucket_name = os.environ.get("BUCKET_NAME", "")
    state_key = os.environ.get("STATE_KEY", "")
    namespace = os.environ.get("STATE_NAMESPACE", "")
    region = os.environ.get("DETECTED_REGION", "")

    # Replace each placeholder
    text = text.replace("__BUCKET__", bucket_name)
    text = text.replace("__KEY__", state_key)
    text = text.replace("__NAMESPACE__", namespace)
    text = text.replace("__REGION__", region)

    return text


def main():
    """
    Main function - This is where the program starts
    """

    # Step 1: Check if we got the right arguments
    if len(sys.argv) != 3:
        print("Error: Missing required arguments")
        print("Usage: python setup_backend.py <cloud-provider> <workspace-path>")
        print("Example: python setup_backend.py oci /path/to/workspace")
        sys.exit(1)

    # Step 2: Get the arguments
    cloud_provider = sys.argv[1]  # "oci" or "azure"
    workspace_path = sys.argv[2]  # Path to the workspace folder

    # Step 3: Check environment variables
    if not check_environment_variables():
        sys.exit(1)

    # Step 4: Choose the right template based on cloud provider
    if cloud_provider == "oci":
        print("Generating OCI provider configuration...")
        config_text = get_oci_template()

    elif cloud_provider == "azure":
        print("Generating Azure provider configuration...")
        config_text = get_azure_template()

    else:
        print(f"Error: Unknown cloud provider '{cloud_provider}'")
        print("Supported providers: oci, azure")
        sys.exit(1)

    # Step 5: Replace placeholders with real values
    config_text = replace_placeholders(config_text)

    # Step 6: Create the file path
    # The file should be at: workspace-path/ORCH/providers.tf
    orch_folder = os.path.join(workspace_path, "ORCH")
    providers_file = os.path.join(orch_folder, "providers.tf")

    # Step 7: Make sure the ORCH folder exists
    if not os.path.exists(orch_folder):
        print(f"Error: ORCH folder does not exist: {orch_folder}")
        sys.exit(1)

    # Step 8: Write the configuration to the file
    with open(providers_file, 'w') as file:
        file.write(config_text)

    # Step 9: Format the file with Terraform
    # Change to the ORCH directory and run terraform fmt
    original_dir = os.getcwd()  # Remember where we are
    os.chdir(orch_folder)       # Go to ORCH folder
    os.system("terraform fmt providers.tf")  # Format the file
    os.chdir(original_dir)      # Go back to original folder

    # Step 10: Print success message
    bucket_name = os.environ.get("BUCKET_NAME", "")
    state_key = os.environ.get("STATE_KEY", "")
    region = os.environ.get("DETECTED_REGION", "")

    print("✅ Terraform backend configuration created successfully")
    print(f"   Backend: OCI")
    print(f"   Bucket: {bucket_name}")
    print(f"   Key: {state_key}")
    print(f"   Region: {region}")


# This line makes the script run when you execute it
if __name__ == "__main__":
    main()
