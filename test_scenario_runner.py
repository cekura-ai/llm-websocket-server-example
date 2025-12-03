"""
Simple test script to verify the scenario runner setup

This script doesn't actually trigger real scenarios - it's for testing the configuration
and understanding the flow before running with real API calls.
"""

import config

def validate_config():
    """Validate the configuration file"""
    print("=" * 60)
    print("Configuration Validation")
    print("=" * 60)

    errors = []
    warnings = []

    # Check API URLs
    print(f"\n✓ API_URL_SERVER_1: {config.API_URL_SERVER_1}")
    print(f"✓ API_URL_SERVER_2: {config.API_URL_SERVER_2}")

    # Check API Keys
    if config.API_KEY_SERVER_1 == "<your-api-key-1>":
        errors.append("API_KEY_SERVER_1 is not configured")
    else:
        print(f"✓ API_KEY_SERVER_1: {'*' * 20} (configured)")

    if config.API_KEY_SERVER_2 == "<your-api-key-2>":
        errors.append("API_KEY_SERVER_2 is not configured")
    else:
        print(f"✓ API_KEY_SERVER_2: {'*' * 20} (configured)")

    # Check Agent IDs
    print(f"✓ AGENT_ID_SERVER_1: {config.AGENT_ID_SERVER_1}")
    print(f"✓ AGENT_ID_SERVER_2: {config.AGENT_ID_SERVER_2}")

    # Check Middleware Settings
    print(f"✓ MIDDLEWARE_HOST: {config.MIDDLEWARE_HOST}")
    print(f"✓ MIDDLEWARE_PORT: {config.MIDDLEWARE_PORT}")

    # Check Scenario Triplets
    print(f"\n✓ Number of scenario triplets: {len(config.SCENARIO_TRIPLETS)}")

    if not config.SCENARIO_TRIPLETS:
        errors.append("No scenario triplets configured")
    else:
        print("\nScenario Triplets:")
        total_runs = 0
        for i, (sid1, sid2, freq) in enumerate(config.SCENARIO_TRIPLETS, 1):
            print(f"  {i}. Scenario {sid1} <-> {sid2} (frequency: {freq})")
            total_runs += freq

        print(f"\nTotal runs that will be executed: {total_runs}")
        print(f"Runs will execute in parallel across {len(config.SCENARIO_TRIPLETS)} triplet(s)")

    # Print errors and warnings
    print("\n" + "=" * 60)
    if errors:
        print("❌ ERRORS:")
        for error in errors:
            print(f"  - {error}")
        print("\n⚠️  Please fix the errors in config.py before running.")
        return False
    else:
        print("✅ Configuration is valid!")

    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    return True


def print_execution_plan():
    """Print the execution plan"""
    print("\n" + "=" * 60)
    print("Execution Plan")
    print("=" * 60)

    print("\nThe scenario runner will:")
    print("1. Start the WebSocket middleware server")
    print("2. Trigger all scenario triplets in PARALLEL")
    print("3. For each triplet:")
    print("   - Run the pair SEQUENTIALLY for the specified frequency")
    print("   - Trigger scenario on server 1 (API call)")
    print("   - Trigger scenario on server 2 (API call)")
    print("   - Register the run_id pair with middleware")
    print("   - Wait for WebSocket connections")
    print("   - Forward messages between matched connections")
    print("4. Keep the server running for connections")

    print("\nExample flow for triplet (12688, 12689, 2):")
    print("  Iteration 1:")
    print("    → Trigger scenario 12688 on server 1 → get run_id_1 (e.g., 47532)")
    print("    → Trigger scenario 12689 on server 2 → get run_id_2 (e.g., 47533)")
    print("    → Register pair: 47532 <-> 47533")
    print("    → Wait for WebSocket with X-Vocera-Run-Id: 47532")
    print("    → Wait for WebSocket with X-Vocera-Run-Id: 47533")
    print("    → Forward messages between them")
    print("  Iteration 2:")
    print("    → Trigger scenario 12688 on server 1 → get run_id_1 (e.g., 47534)")
    print("    → Trigger scenario 12689 on server 2 → get run_id_2 (e.g., 47535)")
    print("    → Register pair: 47534 <-> 47535")
    print("    → Wait for WebSocket with X-Vocera-Run-Id: 47534")
    print("    → Wait for WebSocket with X-Vocera-Run-Id: 47535")
    print("    → Forward messages between them")


def print_next_steps():
    """Print next steps"""
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)

    print("\n1. Review and update config.py with your settings")
    print("2. Ensure your agents are configured to connect to the middleware:")
    print(f"   WebSocket URL: ws://{config.MIDDLEWARE_HOST}:{config.MIDDLEWARE_PORT}")
    print("3. Make sure agents send X-Vocera-Run-Id in WebSocket headers")
    print("4. Run the scenario runner:")
    print("   python scenario_runner.py")
    print("5. Monitor the logs for connection and message forwarding")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Scenario Runner Test & Validation")
    print("=" * 60)

    is_valid = validate_config()

    if is_valid:
        print_execution_plan()

    print_next_steps()

    print("\n" + "=" * 60)
    print()
