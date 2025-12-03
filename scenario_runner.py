import asyncio
import requests
import logging
from typing import List, Tuple
from enhanced_middleware import MultiPairManager, start_middleware_server
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def trigger_scenario(agent_id: int, scenario_id: int, api_key: str, api_url: str) -> int:
    """
    Trigger a scenario on a server and return the run_id

    Args:
        agent_id: The agent ID for the server
        scenario_id: The scenario ID to run
        api_key: The API key for authentication
        api_url: The API URL for the server

    Returns:
        The run_id from the API response
    """
    payload = {
        "agent_id": agent_id,
        "scenarios": [scenario_id],
        "frequency": 1,
    }
    headers = {
        "X-CEKURA-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    try:
        logger.info(f"Triggering scenario {scenario_id} on agent {agent_id} at {api_url}")
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()

        run_id = response.json()['id']
        logger.info(f"Scenario {scenario_id} triggered successfully. Run ID: {run_id}")
        return run_id

    except Exception as e:
        logger.error(f"Error triggering scenario {scenario_id}: {str(e)}")
        raise


async def run_scenario_pair(
    manager: MultiPairManager,
    scenario_id_1: int,
    scenario_id_2: int,
    frequency: int
):
    """
    Run a scenario pair for the specified frequency

    Args:
        manager: The MultiPairManager instance
        scenario_id_1: Scenario ID for server 1
        scenario_id_2: Scenario ID for server 2
        frequency: Number of times to run this pair
    """
    logger.info(f"Starting scenario pair: {scenario_id_1} <-> {scenario_id_2} (frequency: {frequency})")

    for i in range(frequency):
        logger.info(f"Running scenario pair iteration {i+1}/{frequency}")

        try:
            # Trigger both scenarios
            run_id_1 = trigger_scenario(
                config.AGENT_ID_SERVER_1,
                scenario_id_1,
                config.API_KEY_SERVER_1,
                config.API_URL_SERVER_1
            )
            run_id_2 = trigger_scenario(
                config.AGENT_ID_SERVER_2,
                scenario_id_2,
                config.API_KEY_SERVER_2,
                config.API_URL_SERVER_2
            )

            # Register the pair with the middleware
            await manager.register_pair(run_id_1, run_id_2)

            logger.info(f"Registered pair: run_id_1={run_id_1}, run_id_2={run_id_2}")

            # Wait a bit before the next iteration (optional, adjust as needed)
            if i < frequency - 1:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in scenario pair iteration {i+1}: {str(e)}")
            # Continue with next iteration even if one fails
            continue

    logger.info(f"Completed scenario pair: {scenario_id_1} <-> {scenario_id_2}")


async def run_all_scenarios(
    manager: MultiPairManager,
    scenario_triplets: List[Tuple[int, int, int]]
):
    """
    Run all scenario triplets in parallel

    Args:
        manager: The MultiPairManager instance
        scenario_triplets: List of (scenario_id_1, scenario_id_2, frequency) tuples
    """
    logger.info(f"Starting {len(scenario_triplets)} scenario triplets")

    # Create tasks for all scenario pairs
    tasks = []
    for scenario_id_1, scenario_id_2, frequency in scenario_triplets:
        task = asyncio.create_task(
            run_scenario_pair(manager, scenario_id_1, scenario_id_2, frequency)
        )
        tasks.append(task)

    # Wait for all tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("All scenario triplets completed")


async def main(scenario_triplets: List[Tuple[int, int, int]]):
    """
    Main function to start the middleware and run scenarios

    Args:
        scenario_triplets: List of (scenario_id_1, scenario_id_2, frequency) tuples
    """
    # Create the manager
    manager = MultiPairManager()

    # Start the middleware server
    logger.info("Starting middleware server...")
    server = await start_middleware_server(manager, host=config.MIDDLEWARE_HOST, port=config.MIDDLEWARE_PORT)

    try:
        # Run all scenarios
        await run_all_scenarios(manager, scenario_triplets)

        # Keep the server running to handle any remaining connections
        logger.info("Scenarios triggered. Keeping server alive for connections...")
        logger.info("Press Ctrl+C to stop the server")

        # Wait indefinitely
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    # Load scenario triplets from config
    # You can also pass custom triplets here if needed
    scenario_triplets = config.SCENARIO_TRIPLETS

    logger.info(f"Loaded {len(scenario_triplets)} scenario triplets from config")

    try:
        asyncio.run(main(scenario_triplets))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
