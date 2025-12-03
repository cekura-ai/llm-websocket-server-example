import asyncio
import json
import websockets
from typing import Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentPair:
    """Manages a pair of connected agents"""
    def __init__(self):
        self.agent_a: Optional[websockets.WebSocketServerProtocol] = None
        self.agent_b: Optional[websockets.WebSocketServerProtocol] = None
        self.agent_a_task: Optional[asyncio.Task] = None
        self.agent_b_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    async def add_agent(self, websocket: websockets.WebSocketServerProtocol) -> str:
        """Add an agent to the pair. Returns 'A' or 'B' or 'full' if pair is complete"""
        async with self.lock:
            if self.agent_a is None:
                self.agent_a = websocket
                logger.info(f"Agent A connected: {websocket.remote_address}")
                return 'A'
            elif self.agent_b is None:
                self.agent_b = websocket
                logger.info(f"Agent B connected: {websocket.remote_address}")
                return 'B'
            else:
                return 'full'

    async def remove_agent(self, agent_id: str):
        """Remove an agent from the pair"""
        async with self.lock:
            if agent_id == 'A':
                self.agent_a = None
                if self.agent_a_task:
                    self.agent_a_task.cancel()
                logger.info("Agent A disconnected")
            elif agent_id == 'B':
                self.agent_b = None
                if self.agent_b_task:
                    self.agent_b_task.cancel()
                logger.info("Agent B disconnected")

    def is_pair_complete(self) -> bool:
        """Check if both agents are connected"""
        return self.agent_a is not None and self.agent_b is not None

    async def forward_message(self, from_agent: str, message: str):
        """Forward a message from one agent to the other"""
        try:
            if from_agent == 'A' and self.agent_b:
                await self.agent_b.send(message)
                logger.info(f"Forwarded message A -> B: {message[:100]}...")
            elif from_agent == 'B' and self.agent_a:
                await self.agent_a.send(message)
                logger.info(f"Forwarded message B -> A: {message[:100]}...")
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Could not forward message - connection closed")
        except Exception as e:
            logger.error(f"Error forwarding message: {str(e)}")


async def handle_agent_messages(pair: AgentPair, agent_id: str, websocket: websockets.WebSocketServerProtocol):
    """Handle incoming messages from an agent and forward to the other"""
    try:
        # Wait for both agents to be connected
        while not pair.is_pair_complete():
            await asyncio.sleep(0.1)

        logger.info(f"Agent {agent_id} ready for communication")

        # Listen for messages and forward them
        async for message in websocket:
            logger.info(f"Received from Agent {agent_id}:")
            logger.info(f"  Message type: {type(message).__name__}")
            logger.info(f"  Message length: {len(message)} bytes")
            logger.info(f"  Message content: {message[:100]}...")

            # Forward the message to the other agent
            await pair.forward_message(agent_id, message)

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Agent {agent_id} connection closed")
    except Exception as e:
        logger.error(f"Error handling Agent {agent_id}: {str(e)}")
    finally:
        await pair.remove_agent(agent_id)


async def handle_websocket(websocket: websockets.WebSocketServerProtocol, pair: AgentPair):
    """Handle a new WebSocket connection"""
    # Log the request headers
    logger.info(f"Connection from {websocket.remote_address}")
    logger.info("Request Headers:")
    try:
        # Try newer websockets API (v11+)
        if hasattr(websocket, 'request') and hasattr(websocket.request, 'headers'):
            for header, value in websocket.request.headers.raw_items():
                logger.info(f"  {header}: {value}")
        # Fallback to older API
        elif hasattr(websocket, 'request_headers'):
            for header, value in websocket.request_headers.raw_items():
                logger.info(f"  {header}: {value}")
        else:
            logger.info("  Headers not available in this websockets version")
    except Exception as e:
        logger.warning(f"Could not log headers: {e}")

    agent_id = await pair.add_agent(websocket)

    if agent_id == 'full':
        await websocket.send(json.dumps({
            "type": "error",
            "content": "Agent pair is already full. Connection rejected."
        }))
        await websocket.close()
        logger.warning(f"Rejected connection from {websocket.remote_address} - pair already full")
        return

    # Handle messages for this agent
    await handle_agent_messages(pair, agent_id, websocket)


async def main():
    # Create a single agent pair
    pair = AgentPair()

    # Create the WebSocket server
    async def connection_handler(websocket):
        await handle_websocket(websocket, pair)

    server = await websockets.serve(
        connection_handler,
        "127.0.0.1",
        8765
    )

    logger.info("WebSocket middleware server started on ws://127.0.0.1:8765")
    logger.info("Waiting for two agents to connect...")

    await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
