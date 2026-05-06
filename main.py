import asyncio
import json
import aiohttp
import websockets
from openai import AsyncOpenAI

# Configure your OpenAI API key
api_key = 'YOUR-OPENAI-API-KEY'

# Module-level async client — reuses a single connection pool across all concurrent calls
client = AsyncOpenAI(api_key=api_key)

# Store chat histories for different connections
chat_histories = {}

# Define system prompt
SYSTEM_PROMPT = {
    "role": "system",
    "content": """Your system prompt"""
}

# Tool definitions — add your tools here
TOOLS = [
    # Example:
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "my_tool",
    #         "description": "...",
    #         "parameters": { ... }
    #     }
    # }
]

# Map tool names to their endpoint URLs
TOOL_URLS = {
    # "my_tool": "https://example.com/api/my_tool/",
}


async def call_tool(name: str, args: dict) -> str:
    url = TOOL_URLS.get(name)
    if not url:
        return json.dumps({"error": f"Unknown tool: {name}"})
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=args) as resp:
            result = await resp.json()
            return json.dumps(result)


async def chat_response(message, session_id):
    try:
        # Get or create chat history for this session
        if session_id not in chat_histories:
            chat_histories[session_id] = [SYSTEM_PROMPT]

        # Add user message to history
        chat_histories[session_id].append({
            "role": "user",
            "content": message
        })

        # Agentic loop — keeps going until the model returns a plain text response
        while True:
            kwargs = dict(
                model="gpt-4o-2024-08-06",
                messages=chat_histories[session_id],
                temperature=0.0,
            )
            if TOOLS:
                kwargs["tools"] = TOOLS
                kwargs["tool_choice"] = "auto"

            # AsyncOpenAI is truly non-blocking — event loop stays free for ping/pong
            response = await client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            if TOOLS and choice.finish_reason == "tool_calls":
                assistant_msg = choice.message
                chat_histories[session_id].append(assistant_msg)
                for tool_call in assistant_msg.tool_calls:
                    args = json.loads(tool_call.function.arguments)
                    print(f"Tool call: {tool_call.function.name}({args})")
                    result = await call_tool(tool_call.function.name, args)
                    print(f"Tool result: {result}")
                    chat_histories[session_id].append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                assistant_response = choice.message.content
                chat_histories[session_id].append({
                    "role": "assistant",
                    "content": assistant_response,
                })
                break

        # Limit context window to last 10 messages (adjust as needed)
        if len(chat_histories[session_id]) > 12:  # system prompt + 10 exchanges
            chat_histories[session_id] = [
                chat_histories[session_id][0]  # Keep system prompt
            ] + chat_histories[session_id][-10:]  # Keep last 10 messages

        return json.dumps({"content": assistant_response})
    except Exception as e:
        return f"Error: {str(e)}"


async def handle_websocket(websocket, path):
    # Generate unique session ID for this connection
    session_id = id(websocket)

    try:
        await websocket.send(json.dumps({"content": "Hi! How can I help you today?"}))
        async for message in websocket:
            message = json.loads(message)["content"]
            print(f"Received message: {message}")

            # Get response from OpenAI
            response = await chat_response(message, session_id)

            # Send response back to client
            await websocket.send(response)
            print(f"Sent response: {response}")

    except websockets.exceptions.ConnectionClosed:
        # Clean up chat history when connection closes
        if session_id in chat_histories:
            del chat_histories[session_id]
    except Exception as e:
        print(f"Error: {str(e)}")


async def main():
    server = await websockets.serve(
        handle_websocket,
        "0.0.0.0",
        8765,
        ping_interval=None,  # Disable server→client pings; let the client manage keepalive
    )
    print("WebSocket server started on ws://0.0.0.0:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
