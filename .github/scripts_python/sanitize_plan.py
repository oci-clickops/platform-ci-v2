#!/usr/bin/env python3
"""
Sanitize Terraform plan output - Remove sensitive information
This script removes passwords, IDs, and keys from Terraform output
"""

# Import the 're' library to do find-and-replace with patterns
import re
# Import 'sys' to read command line arguments
import sys


def sanitize_oci_data(text):
    """
    Remove sensitive OCI data from text

    What this does:
    - Finds OCI IDs (they look like: ocid1.tenancy.oc1..aaa123)
    - Finds passwords
    - Replaces them with *** to hide them
    """

    # Step 1: Hide OCI IDs
    # OCIDs look like: ocid1.something.oc1.region.randomletters
    text = re.sub(r'ocid1\.[a-z]+\.[a-z0-9]+\.[^.]+\.[a-z0-9]+', 'ocid1.***REDACTED***', text)

    # Step 2: Hide tenancy_ocid (the main account ID)
    # This works with or without quotes around the variable name
    text = re.sub(r'"?tenancy_ocid"?\s*=\s*"[^"]+"', 'tenancy_ocid = "***"', text)

    # Step 3: Hide compartment_id (folder/group ID)
    # This works with or without quotes around the variable name
    text = re.sub(r'"?compartment_id"?\s*=\s*"[^"]+"', 'compartment_id = "***"', text)

    # Step 4: Hide database passwords
    text = re.sub(r'admin_password\s*=\s*"[^"]+"', 'admin_password = "***"', text)

    # Step 5: Hide password placeholders
    text = re.sub(r'__ATP_ADMIN_PASSWORD__', '***', text)

    return text


def sanitize_azure_data(text):
    """
    Remove sensitive Azure data from text

    What this does:
    - Finds Azure subscription IDs (they look like UUIDs)
    - Finds SSH keys
    - Replaces them with *** to hide them
    """

    # Step 1: Hide subscription paths
    # They look like: /subscriptions/123e4567-e89b-12d3-a456-426614174000
    text = re.sub(r'/subscriptions/[a-f0-9-]{36}', '/subscriptions/***', text)

    # Step 2: Hide tenant_id (the directory ID)
    # This works with or without quotes around the variable name
    text = re.sub(r'"?tenant_id"?\s*=\s*"[a-f0-9-]{36}"', 'tenant_id = "***"', text)

    # Step 3: Hide subscription_id
    # This works with or without quotes around the variable name
    text = re.sub(r'"?subscription_id"?\s*=\s*"[a-f0-9-]{36}"', 'subscription_id = "***"', text)

    # Step 4: Hide SSH keys (they start with ssh-rsa and are very long)
    text = re.sub(r'ssh-rsa AAAA[A-Za-z0-9+/=]{300,}', 'ssh-rsa ***REDACTED***', text)

    # Step 5: Hide public key blocks
    text = re.sub(
        r'-----BEGIN PUBLIC KEY-----[^-]*-----END PUBLIC KEY-----',
        '***PUBLIC_KEY_REDACTED***',
        text
    )

    return text


def main():
    """
    Main function - This is where the program starts
    """

    # Step 1: Check if we got the right number of arguments
    # We need: python script.py <cloud> <plan-text>
    if len(sys.argv) != 3:
        print("Error: Wrong number of arguments")
        print("Usage: python sanitize_plan.py <cloud> <plan-output>")
        print("Example: python sanitize_plan.py oci 'some plan text'")
        sys.exit(1)

    # Step 2: Get the arguments
    cloud_provider = sys.argv[1]  # First argument: "oci" or "azure"
    plan_output = sys.argv[2]      # Second argument: the plan text to clean

    # Step 3: Sanitize based on which cloud we're using
    if cloud_provider == "oci":
        # Use OCI sanitization
        clean_output = sanitize_oci_data(plan_output)

    elif cloud_provider == "azure":
        # Use Azure sanitization
        clean_output = sanitize_azure_data(plan_output)

    else:
        # We don't support this cloud provider
        print(f"Error: Unknown cloud provider '{cloud_provider}'")
        print("Supported providers: oci, azure")
        sys.exit(1)

    # Step 4: Print the cleaned output
    print(clean_output)


# This line makes the script run when you execute it
if __name__ == "__main__":
    main()
