import asyncio
import json
import websockets
from typing import Optional, Dict, Set
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RunIdPair:
    """Represents a pair of run_ids that should be connected"""
    run_id_1: int
    run_id_2: int
    websocket_1: Optional[websockets.WebSocketServerProtocol] = None
    websocket_2: Optional[websockets.WebSocketServerProtocol] = None
    task_1: Optional[asyncio.Task] = None
    task_2: Optional[asyncio.Task] = None


class MultiPairManager:
    """Manages multiple pairs of agents based on run_ids"""
    def __init__(self):
        self.expected_pairs: Dict[int, RunIdPair] = {}  # run_id -> RunIdPair
        self.active_pairs: Dict[int, RunIdPair] = {}  # run_id -> RunIdPair
        self.lock = asyncio.Lock()

    async def register_pair(self, run_id_1: int, run_id_2: int):
        """Register a new expected pair of run_ids"""
        async with self.lock:
            pair = RunIdPair(run_id_1=run_id_1, run_id_2=run_id_2)
            self.expected_pairs[run_id_1] = pair
            self.expected_pairs[run_id_2] = pair
            logger.info(f"Registered pair: run_id_1={run_id_1}, run_id_2={run_id_2}")

    async def add_connection(self, run_id: int, websocket: websockets.WebSocketServerProtocol) -> Optional[RunIdPair]:
        """Add a websocket connection for a given run_id"""
        async with self.lock:
            if run_id not in self.expected_pairs:
                logger.warning(f"Unexpected connection with run_id={run_id}")
                return None

            pair = self.expected_pairs[run_id]

            # Determine which side of the pair this is
            if run_id == pair.run_id_1:
                pair.websocket_1 = websocket
                logger.info(f"Connected run_id_1={run_id} (paired with run_id_2={pair.run_id_2})")
            elif run_id == pair.run_id_2:
                pair.websocket_2 = websocket
                logger.info(f"Connected run_id_2={run_id} (paired with run_id_1={pair.run_id_1})")

            # If both sides are connected, move to active pairs
            if pair.websocket_1 and pair.websocket_2:
                self.active_pairs[pair.run_id_1] = pair
                self.active_pairs[pair.run_id_2] = pair
                logger.info(f"Pair complete and active: {pair.run_id_1} <-> {pair.run_id_2}")

            return pair

    async def remove_connection(self, run_id: int):
        """Remove a connection and cleanup"""
        async with self.lock:
            if run_id in self.active_pairs:
                pair = self.active_pairs[run_id]

                # Cancel tasks
                if pair.task_1:
                    pair.task_1.cancel()
                if pair.task_2:
                    pair.task_2.cancel()

                # Remove from active and expected
                self.active_pairs.pop(pair.run_id_1, None)
                self.active_pairs.pop(pair.run_id_2, None)
                self.expected_pairs.pop(pair.run_id_1, None)
                self.expected_pairs.pop(pair.run_id_2, None)

                logger.info(f"Removed pair: {pair.run_id_1} <-> {pair.run_id_2}")

    def is_pair_complete(self, pair: RunIdPair) -> bool:
        """Check if both sides of a pair are connected"""
        return pair.websocket_1 is not None and pair.websocket_2 is not None


def extract_run_id(websocket: websockets.WebSocketServerProtocol) -> Optional[int]:
    """Extract result_id from WebSocket headers (using X-Vocera-Result-Id)"""
    try:
        if hasattr(websocket, 'request') and hasattr(websocket.request, 'headers'):
            headers = websocket.request.headers
            for header, value in headers.raw_items():
                if header.lower() == 'x-vocera-result-id':
                    return int(value)
        elif hasattr(websocket, 'request_headers'):
            headers = websocket.request_headers
            for header, value in headers.raw_items():
                if header.lower() == 'x-vocera-result-id':
                    return int(value)
    except Exception as e:
        logger.error(f"Error extracting result_id: {e}")

    return None


async def forward_messages(pair: RunIdPair, run_id: int):
    """Forward messages from one websocket to its pair"""
    try:
        # Wait for both to be connected
        while not (pair.websocket_1 and pair.websocket_2):
            await asyncio.sleep(0.1)

        # Determine which websocket is the source and which is the destination
        # IMPORTANT: Do this AFTER both are connected
        if run_id == pair.run_id_1:
            source = pair.websocket_1
            dest = pair.websocket_2
            source_label = f"run_id_1={run_id}"
            dest_label = f"run_id_2={pair.run_id_2}"
        else:
            source = pair.websocket_2
            dest = pair.websocket_1
            source_label = f"run_id_2={run_id}"
            dest_label = f"run_id_1={pair.run_id_1}"

        logger.info(f"{source_label} ready for communication")

        # Forward messages
        async for message in source:
            try:
                logger.info(f"Received from {source_label}:")
                logger.info(f"  Message type: {type(message).__name__}")
                logger.info(f"  Message length: {len(message)} bytes")
                logger.info(f"  Message content: {message[:100]}...")

                await dest.send(message)
                logger.info(f"Forwarded {source_label} -> {dest_label}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Could not forward message - {dest_label} connection closed")
                break
            except Exception as e:
                logger.error(f"Error forwarding message: {str(e)}")

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"{source_label} connection closed")
    except Exception as e:
        logger.error(f"Error in forward_messages for {source_label}: {str(e)}")


async def handle_websocket(websocket: websockets.WebSocketServerProtocol, manager: MultiPairManager):
    """Handle a new WebSocket connection"""
    # Log the request headers
    logger.info(f"Connection from {websocket.remote_address}")
    logger.info("Request Headers:")
    try:
        if hasattr(websocket, 'request') and hasattr(websocket.request, 'headers'):
            for header, value in websocket.request.headers.raw_items():
                logger.info(f"  {header}: {value}")
        elif hasattr(websocket, 'request_headers'):
            for header, value in websocket.request_headers.raw_items():
                logger.info(f"  {header}: {value}")
    except Exception as e:
        logger.warning(f"Could not log headers: {e}")

    # Extract result_id from headers (this is what the API returns as 'id')
    run_id = extract_run_id(websocket)

    if run_id is None:
        error_msg = "Missing or invalid X-Vocera-Result-Id header"
        logger.error(error_msg)
        await websocket.send(json.dumps({
            "type": "error",
            "content": error_msg
        }))
        await websocket.close()
        return

    # Add connection to manager
    pair = await manager.add_connection(run_id, websocket)

    if pair is None:
        error_msg = f"No expected pair found for run_id={run_id}"
        logger.warning(error_msg)
        await websocket.send(json.dumps({
            "type": "error",
            "content": error_msg
        }))
        await websocket.close()
        return

    # Start forwarding messages
    try:
        await forward_messages(pair, run_id)
    finally:
        await manager.remove_connection(run_id)


async def start_middleware_server(manager: MultiPairManager, host: str = "127.0.0.1", port: int = 8765):
    """Start the WebSocket middleware server"""
    async def connection_handler(websocket):
        await handle_websocket(websocket, manager)

    server = await websockets.serve(
        connection_handler,
        host,
        port
    )

    logger.info(f"WebSocket middleware server started on ws://{host}:{port}")
    logger.info("Waiting for agent connections...")

    return server


async def main():
    # Create the manager
    manager = MultiPairManager()

    # Start the middleware server
    server = await start_middleware_server(manager)

    # Keep the server running
    await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
