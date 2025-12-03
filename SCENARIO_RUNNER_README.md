# Scenario Runner with Enhanced Middleware

This system allows you to run multiple scenario pairs in parallel, with the middleware automatically matching and coordinating WebSocket connections based on run IDs.

## Architecture

The system consists of three main components:

1. **enhanced_middleware.py** - WebSocket middleware that handles multiple agent pairs simultaneously
2. **scenario_runner.py** - Script that triggers scenarios and manages the workflow
3. **config.py** - Configuration file for API keys and scenario triplets

## How It Works

1. The scenario runner triggers scenarios on both servers using the API
2. Each API call returns a `run_id`
3. The middleware registers these run_id pairs as expected connections
4. When WebSocket connections arrive with `X-Vocera-Run-Id` headers, the middleware matches them
5. Once both sides of a pair are connected, messages are forwarded between them

## Setup

1. **Install dependencies:**
   ```bash
   pip install websockets requests
   ```

2. **Configure your settings in config.py:**
   ```python
   # Update these with your actual values
   API_KEY_SERVER_1 = "your-api-key-1"
   API_KEY_SERVER_2 = "your-api-key-2"
   AGENT_ID_SERVER_1 = 6333
   AGENT_ID_SERVER_2 = 789
   ```

3. **Define your scenario triplets in config.py:**
   ```python
   SCENARIO_TRIPLETS = [
       (scenario_id_1, scenario_id_2, frequency),
       # Example:
       (12688, 12689, 2),   # Run scenario 12688 with 12689, 2 times
       (12690, 12691, 1),   # Run scenario 12690 with 12691, 1 time
   ]
   ```

## Usage

### Running the Complete System

Simply run the scenario runner, which will start the middleware and trigger all scenarios:

```bash
python scenario_runner.py
```

This will:
1. Start the WebSocket middleware server on port 8765
2. Trigger all scenario pairs in parallel
3. For each triplet's frequency, run the scenarios sequentially
4. Keep the server running to handle connections

### Running Only the Middleware

If you want to run just the middleware (for testing or manual scenario triggering):

```bash
python enhanced_middleware.py
```

## Scenario Triplet Format

Each triplet is a tuple of three values:
- `scenario_id_1` (int): Scenario ID to run on server 1
- `scenario_id_2` (int): Scenario ID to run on server 2
- `frequency` (int): Number of times to run this scenario pair

Example:
```python
(12688, 12689, 3)
# This will:
# - Run scenario 12688 on server 1 and scenario 12689 on server 2
# - Repeat this 3 times sequentially
# - Each run gets a unique run_id pair
```

## Execution Flow

### For Multiple Triplets
```python
SCENARIO_TRIPLETS = [
    (12688, 12689, 2),
    (12690, 12691, 1),
    (12692, 12693, 3),
]
```

The runner will:
1. Start all triplets **in parallel**
2. For each triplet:
   - Run frequency times **sequentially**
   - Trigger both scenarios (get run_id_1 and run_id_2)
   - Register the pair with middleware
   - Wait for WebSocket connections
   - Forward messages between matched connections

## Logging

The system provides detailed logging:
- Connection events with headers
- Run ID registrations and pairings
- Message forwarding details
- Error handling

Example log output:
```
2025-12-01 15:24:44 - INFO - Starting middleware server...
2025-12-01 15:24:44 - INFO - WebSocket middleware server started on ws://127.0.0.1:8765
2025-12-01 15:24:45 - INFO - Triggering scenario 12688 on agent 6333
2025-12-01 15:24:45 - INFO - Scenario 12688 triggered successfully. Run ID: 47532
2025-12-01 15:24:46 - INFO - Triggering scenario 12689 on agent 789
2025-12-01 15:24:46 - INFO - Scenario 12689 triggered successfully. Run ID: 47533
2025-12-01 15:24:46 - INFO - Registered pair: run_id_1=47532, run_id_2=47533
2025-12-01 15:24:47 - INFO - Connection from ('127.0.0.1', 50295)
2025-12-01 15:24:47 - INFO - Request Headers:
2025-12-01 15:24:47 - INFO -   X-Vocera-Run-Id: 47532
2025-12-01 15:24:47 - INFO - Connected run_id_1=47532 (paired with run_id_2=47533)
2025-12-01 15:24:48 - INFO - Connection from ('127.0.0.1', 50296)
2025-12-01 15:24:48 - INFO -   X-Vocera-Run-Id: 47533
2025-12-01 15:24:48 - INFO - Connected run_id_2=47533 (paired with run_id_1=47532)
2025-12-01 15:24:48 - INFO - Pair complete and active: 47532 <-> 47533
2025-12-01 15:24:48 - INFO - Forwarded run_id_1=47532 -> run_id_2=47533
```

## Features

- **Multiple concurrent pairs**: Handle many scenario pairs simultaneously
- **Run ID matching**: Automatically pair WebSocket connections based on X-Vocera-Run-Id header
- **Parallel execution**: All triplets run in parallel for faster execution
- **Sequential frequency**: Each triplet's frequency runs execute sequentially
- **Error handling**: Graceful error handling and logging
- **Flexible configuration**: Easy to configure via config.py

## Troubleshooting

### Connection refused
- Ensure the middleware server is running before scenarios are triggered
- Check that the WebSocket URL in your agents points to the middleware (ws://127.0.0.1:8765)

### Run IDs not matching
- Verify that the X-Vocera-Run-Id header is being sent by the agents
- Check the logs to see which run_ids are being registered and which are connecting

### API errors
- Verify your API keys are correct in config.py
- Check that agent IDs are correct
- Ensure scenario IDs exist and are accessible

## Files

- **enhanced_middleware.py**: The WebSocket middleware server with multi-pair support
- **scenario_runner.py**: Main script to run scenarios
- **config.py**: Configuration file (API keys, agent IDs, scenario triplets)
- **middleware.py**: Original simple middleware (kept for reference)

## Notes

- The middleware server stays running after triggering scenarios to handle connections
- Press Ctrl+C to stop the server
- WebSocket connections must include the X-Vocera-Run-Id header to be paired correctly
