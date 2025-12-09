#!/usr/bin/env python3
"""
Simple tests for the Python scripts
Run this to make sure everything works!
"""

# Import libraries we need
import subprocess  # To run the scripts
import os          # To set environment variables
import tempfile    # To create temporary test files
import sys         # To exit with error codes


def test_sanitize_oci():
    """
    Test that sanitize_plan.py hides OCI sensitive data
    """
    print("Testing sanitize_plan.py with OCI...")

    # Input text with sensitive data
    test_input = 'tenancy_ocid = "ocid1.tenancy.oc1..aaa123456"'

    # Run the script
    result = subprocess.run(
        ['python3', 'sanitize_plan.py', 'oci', test_input],
        capture_output=True,  # Capture what the script prints
        text=True             # Get output as text (not bytes)
    )

    # Check if the sensitive data was hidden
    if '***' in result.stdout and 'ocid1.tenancy.oc1..aaa123456' not in result.stdout:
        print("✅ OCI sanitization works!")
        return True
    else:
        print("❌ OCI sanitization failed!")
        print(f"   Output: {result.stdout}")
        return False


def test_sanitize_azure():
    """
    Test that sanitize_plan.py hides Azure sensitive data
    """
    print("Testing sanitize_plan.py with Azure...")

    # Input text with sensitive data
    test_input = 'subscription_id = "12345678-1234-1234-1234-123456789abc"'

    # Run the script
    result = subprocess.run(
        ['python3', 'sanitize_plan.py', 'azure', test_input],
        capture_output=True,
        text=True
    )

    # Check if the sensitive data was hidden
    if '***' in result.stdout and '12345678-1234-1234-1234-123456789abc' not in result.stdout:
        print("✅ Azure sanitization works!")
        return True
    else:
        print("❌ Azure sanitization failed!")
        print(f"   Output: {result.stdout}")
        return False


def test_replace_placeholders():
    """
    Test that replace_placeholders.py replaces placeholders correctly
    """
    print("Testing replace_placeholders.py...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:

        # Create a test JSON file with a placeholder
        test_file = os.path.join(temp_dir, 'test.json')
        with open(test_file, 'w') as f:
            f.write('{"password": "__ATP_ADMIN_PASSWORD__"}')

        # Set the environment variable
        os.environ['ATP_ADMIN_PASSWORD'] = 'secret123'

        # Run the script
        result = subprocess.run(
            ['python3', 'replace_placeholders.py', 'oci', temp_dir],
            capture_output=True,
            text=True
        )

        # Read the file back
        with open(test_file, 'r') as f:
            content = f.read()

        # Check if the placeholder was replaced
        if 'secret123' in content and '__ATP_ADMIN_PASSWORD__' not in content:
            print("✅ Placeholder replacement works!")
            return True
        else:
            print("❌ Placeholder replacement failed!")
            print(f"   File content: {content}")
            return False


def test_discover_backend():
    """
    Test that discover_backend.py accepts bucket name as parameter
    """
    print("Testing discover_backend.py with bucket name parameter...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test structure: oci/eu-frankfurt-1/
        test_cloud_dir = os.path.join(temp_dir, 'oci')
        test_region_dir = os.path.join(test_cloud_dir, 'eu-frankfurt-1')
        os.makedirs(test_region_dir)

        # Set environment variables
        os.environ['GITHUB_OUTPUT'] = os.path.join(temp_dir, 'output.txt')
        os.environ['GITHUB_ENV'] = os.path.join(temp_dir, 'env.txt')

        # Change to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        # Run the script
        result = subprocess.run(
            ['python3', os.path.join(original_dir, 'discover_backend.py'), 'oci', 'test-bucket'],
            capture_output=True,
            text=True
        )

        os.chdir(original_dir)

        # Check if it succeeded
        if result.returncode == 0 and 'test-bucket' in result.stdout:
            print("✅ Backend discovery with bucket parameter works!")
            return True
        else:
            print("❌ Backend discovery failed!")
            print(f"   Output: {result.stdout}")
            print(f"   Error: {result.stderr}")
            return False


def test_setup_backend():
    """
    Test that setup_backend.py creates the providers.tf file
    """
    print("Testing setup_backend.py...")

    # Create a temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:

        # Create ORCH folder
        orch_dir = os.path.join(temp_dir, 'ORCH')
        os.makedirs(orch_dir)

        # Set required environment variables
        os.environ['BUCKET_NAME'] = 'test-bucket'
        os.environ['STATE_KEY'] = 'test-key'
        os.environ['STATE_NAMESPACE'] = 'test-namespace'
        os.environ['DETECTED_REGION'] = 'us-east-1'

        # Run the script (without terraform fmt since we may not have terraform)
        # We'll just check if the file is created
        result = subprocess.run(
            ['python3', 'setup_backend.py', 'oci', temp_dir],
            capture_output=True,
            text=True
        )

        # Check if providers.tf was created
        providers_file = os.path.join(orch_dir, 'providers.tf')
        if os.path.exists(providers_file):
            # Check if placeholders were replaced
            with open(providers_file, 'r') as f:
                content = f.read()

            if 'test-bucket' in content and '__BUCKET__' not in content:
                print("✅ Backend setup works!")
                return True
            else:
                print("❌ Backend setup failed - placeholders not replaced!")
                return False
        else:
            print("❌ Backend setup failed - file not created!")
            return False


def main():
    """
    Run all tests
    """
    print("=" * 60)
    print("Running Simple Tests for Python Scripts")
    print("=" * 60)
    print()

    # Keep track of test results
    results = []

    # Run each test
    results.append(test_sanitize_oci())
    print()

    results.append(test_sanitize_azure())
    print()

    results.append(test_replace_placeholders())
    print()

    results.append(test_discover_backend())
    print()

    results.append(test_setup_backend())
    print()

    # Print summary
    print("=" * 60)
    passed = sum(results)  # Count how many are True
    total = len(results)   # Total number of tests

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)  # Exit with success
    else:
        print("⚠️  Some tests failed!")
        sys.exit(1)  # Exit with error


# This line makes the script run when you execute it
if __name__ == "__main__":
    main()
