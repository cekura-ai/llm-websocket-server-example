import asyncio
import json
import websockets


async def agent_client(agent_name: str, messages_to_send: list):
    """Simulates an agent connecting to the middleware"""
    uri = "ws://127.0.0.1:8766"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{agent_name}] Connected to middleware")

            # Receive initial system messages
            initial_msg = await websocket.recv()
            print(f"[{agent_name}] Received: {initial_msg}")

            # Wait for pair ready message
            ready_msg = await websocket.recv()
            print(f"[{agent_name}] Received: {ready_msg}")

            # Create tasks for sending and receiving
            async def send_messages():
                for i, msg in enumerate(messages_to_send):
                    await asyncio.sleep(2)  # Wait 2 seconds between messages
                    message_json = json.dumps({"content": msg})
                    await websocket.send(message_json)
                    print(f"[{agent_name}] Sent: {msg}")

            async def receive_messages():
                try:
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        print(f"[{agent_name}] Received from other agent: {data.get('content', response)}")
                except websockets.exceptions.ConnectionClosed:
                    print(f"[{agent_name}] Connection closed")

            # Run both tasks concurrently
            await asyncio.gather(
                send_messages(),
                receive_messages()
            )

    except Exception as e:
        print(f"[{agent_name}] Error: {str(e)}")


async def main():
    """Run two test agents"""
    print("Starting test agents...")
    print("Agent 1 will act as a customer")
    print("Agent 2 will act as a support agent\n")

    # Messages for Agent 1 (Customer)
    agent1_messages = [
        "Hello, I need help with my account",
        "My name is Robert",
        "I want to inquire about HDFC mutual fund",
        "My phone number is nine, eight, seven ... six, five, four ... one, two, three, four",
        "My email is robertsmith@gmail.com"
    ]

    # Messages for Agent 2 (Support)
    agent2_messages = [
        "Hello! Welcome to customer support. How can I help you today?",
        "Nice to meet you, Robert. What specifically would you like to know about HDFC mutual fund?",
        "Could you please provide your phone number for verification?",
        "Thank you. Could you also provide your email address?",
        "Thank you for providing all the information. I'll look into your request right away."
    ]

    # Start both agents concurrently
    await asyncio.gather(
        agent_client("Agent-1-Customer", agent1_messages),
        agent_client("Agent-2-Support", agent2_messages)
    )


if __name__ == "__main__":
    asyncio.run(main())
