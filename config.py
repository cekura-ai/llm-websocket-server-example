"""
Configuration file for the scenario runner

Update the values below with your actual API keys and settings
"""

# Server 1 Configuration
API_URL_SERVER_1 = "https://api.cekura.ai/test_framework/v1/scenarios/run_scenarios_text/"
AGENT_ID_SERVER_1 = 6333
API_KEY_SERVER_1 = ""  # Replace with your actual API key for server 1

# Server 2 Configuration
API_URL_SERVER_2 = "http://127.0.0.1:8000/test_framework/v1/scenarios/run_scenarios_text/"
AGENT_ID_SERVER_2 = 789
API_KEY_SERVER_2 = ""  # Replace with your actual API key for server 2

# Middleware Configuration
MIDDLEWARE_HOST = "127.0.0.1"
MIDDLEWARE_PORT = 8765

# Scenario Triplets
# Format: [(scenario_id_1, scenario_id_2, frequency), ...]
# - scenario_id_1: Scenario to run on server 1
# - scenario_id_2: Scenario to run on server 2
# - frequency: Number of times to run this pair
SCENARIO_TRIPLETS = [
    (72235, 12732, 1)
    # Add more triplets as needed
]
