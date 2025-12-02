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
    Test that discover_backend.py parses repository names correctly
    """
    print("Testing discover_backend.py repository name parsing...")

    # Import the function we want to test
    sys.path.insert(0, os.path.dirname(__file__))
    from discover_backend import get_repository_name

    test_cases = [
        ("oci-clickops/oe-env-project-template", "project"),
        ("oci-clickops/oe-env-myapp", "myapp"),
        ("oci-clickops/oe-env-my-new-app", "my-new-app"),
        ("owner/oe-env-test", "test"),
    ]

    all_passed = True
    for repo_full_name, expected_bucket in test_cases:
        # Set the environment variable
        os.environ['GITHUB_REPOSITORY'] = repo_full_name

        # Call the function
        result = get_repository_name()

        # Check result
        if result == expected_bucket:
            print(f"   ✓ {repo_full_name} → {result}")
        else:
            print(f"   ✗ {repo_full_name} → {result} (expected: {expected_bucket})")
            all_passed = False

    if all_passed:
        print("✅ Repository name parsing works!")
        return True
    else:
        print("❌ Repository name parsing failed!")
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
