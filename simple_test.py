import asyncio
import json
import websockets


async def simple_agent(agent_name: str, message_delay: float = 3.0):
    """Simple agent that echoes received messages with a prefix"""
    uri = "ws://127.0.0.1:8766"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{agent_name}] Connected to middleware")

            # Receive initial system messages
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)
                print(f"[{agent_name}] {data}")

                if "Pair is ready" in data.get("content", ""):
                    break

            print(f"[{agent_name}] Ready to chat!\n")

            # Listen and respond
            async def listen():
                try:
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        content = data.get("content", "")
                        print(f"\n[{agent_name}] 📨 Received: {content}")

                        # Send a response after a delay
                        await asyncio.sleep(message_delay)
                        response = f"[{agent_name} response] I received your message: '{content}'. How can I help further?"
                        response_json = json.dumps({"content": response})
                        await websocket.send(response_json)
                        print(f"[{agent_name}] 📤 Sent: {response}\n")

                except websockets.exceptions.ConnectionClosed:
                    print(f"[{agent_name}] Connection closed")

            await listen()

    except Exception as e:
        print(f"[{agent_name}] Error: {str(e)}")


async def main():
    print("=" * 70)
    print("Starting Simple Middleware Test")
    print("=" * 70)
    print("This test creates two simple agents that echo messages to each other")
    print("Agent-1 will send an initial message, then both agents will respond")
    print("=" * 70)
    print()

    async def agent1():
        await asyncio.sleep(1)  # Wait for both to connect
        uri = "ws://127.0.0.1:8766"
        async with websockets.connect(uri) as websocket:
            print("[Agent-1] Connected")

            # Receive system messages
            msg1 = await websocket.recv()
            print(f"[Agent-1] {json.loads(msg1)}")
            msg2 = await websocket.recv()
            print(f"[Agent-1] {json.loads(msg2)}")
            print()

            # Send initial message
            await asyncio.sleep(1)
            initial = json.dumps({"content": "Hello! I'm Agent-1. Nice to meet you!"})
            await websocket.send(initial)
            print(f"[Agent-1] 📤 Sent: Hello! I'm Agent-1. Nice to meet you!\n")

            # Listen for responses
            try:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"\n[Agent-1] 📨 Received: {data.get('content', '')}")

                    await asyncio.sleep(2)
                    response = json.dumps({"content": "Thanks for your response! This is working great."})
                    await websocket.send(response)
                    print(f"[Agent-1] 📤 Sent: Thanks for your response! This is working great.\n")

            except websockets.exceptions.ConnectionClosed:
                print("[Agent-1] Connection closed")

    async def agent2():
        await simple_agent("Agent-2", message_delay=2.0)

    # Start both agents
    await asyncio.gather(agent1(), agent2())


if __name__ == "__main__":
    print("\n⚠️  Make sure the middleware server is running first!")
    print("    Run: python middleware.py\n")
    input("Press Enter to start the test agents...")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest stopped by user")
