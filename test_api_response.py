"""
Quick test to check the API response structure
"""
import requests
import json
import config

# Test triggering a scenario and see what the response looks like
payload = {
    "agent_id": config.AGENT_ID_SERVER_1,
    "scenarios": [72235],
    "frequency": 1,
}
headers = {
    "X-CEKURA-API-KEY": config.API_KEY_SERVER_1,
    "Content-Type": "application/json"
}

print("Testing API call to server 1...")
print(f"URL: {config.API_URL_SERVER_1}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\n" + "="*60)

try:
    response = requests.post(config.API_URL_SERVER_1, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON:")
    print(json.dumps(response.json(), indent=2))

    # Try to extract the run_id
    response_data = response.json()
    if 'id' in response_data:
        print(f"\n✓ Found 'id' field: {response_data['id']}")
    else:
        print(f"\n❌ No 'id' field found in response!")
        print(f"Available fields: {list(response_data.keys())}")

except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'response'):
        print(f"Response text: {e.response.text}")
