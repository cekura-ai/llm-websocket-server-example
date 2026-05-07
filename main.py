import asyncio
import json
import os
import httpx
import websockets
from openai import AsyncOpenAI

# Configure your OpenAI API key
api_key = os.environ.get("OPENAI_API_KEY", "YOUR-OPENAI-API-KEY")

# Module-level async client — reuses a single connection pool across all concurrent calls.
# 60s timeout per attempt; retried up to the RETRY_BUDGET before giving up.
client = AsyncOpenAI(
    api_key=api_key,
    timeout=httpx.Timeout(timeout=60.0, connect=5.0),
)

# Semaphore caps concurrent LLM calls to prevent rate-limit pile-ups under load.
_llm_semaphore = asyncio.Semaphore(8)

# Total time budget for retrying transient LLM failures (stay within any upstream
# inactivity timeout — e.g. Cekura's 5-minute window).
_RETRY_BUDGET_SECONDS = 270

# Store chat histories for different connections
chat_histories = {}

# Define system prompt
SYSTEM_PROMPT = {
    "role": "system",
    "content": """Your system prompt"""
}


async def _llm_call(messages: list) -> str:
    """
    Call the LLM with retries on transient errors (timeout, rate-limit, 503 …).
    Returns the assistant's text content.
    """
    start = asyncio.get_event_loop().time()
    attempt = 0
    while True:
        try:
            async with _llm_semaphore:
                response = await client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=messages,
                    temperature=0.0,
                )
            return response.choices[0].message.content
        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start
            err = str(e).lower()
            retryable = any(k in err for k in ("timeout", "rate", "429", "503", "connection", "overloaded"))
            if retryable and elapsed < _RETRY_BUDGET_SECONDS:
                wait = min(2 ** attempt, 30)
                attempt += 1
                print(f"LLM call failed (attempt {attempt}, elapsed {elapsed:.0f}s): {e} — retrying in {wait}s")
                await asyncio.sleep(wait)
            else:
                raise


async def chat_response(message: str, session_id: int, websocket=None) -> str:
    """
    Process one user turn and return a JSON-encoded response.

    A single outer keepalive task runs for the full duration of this function,
    sending a metadata frame every 8 seconds.  This resets any upstream
    inactivity checker (e.g. Cekura's) so the connection is never dropped
    while the LLM is thinking — even under heavy concurrent load.

    The keepalive is the *only* place we send to the WebSocket during
    processing; no inner keepalive runs inside _llm_call, which avoids the
    concurrent-send race condition that can corrupt WebSocket frames.
    """
    async def keepalive():
        while True:
            await asyncio.sleep(8)
            try:
                if websocket:
                    await websocket.send(json.dumps({"metadata": {"keepalive": True}}))
            except Exception:
                break

    ka_task = asyncio.create_task(keepalive()) if websocket else None
    try:
        if session_id not in chat_histories:
            chat_histories[session_id] = [SYSTEM_PROMPT]

        chat_histories[session_id].append({"role": "user", "content": message})

        assistant_response = await _llm_call(chat_histories[session_id])

        chat_histories[session_id].append({"role": "assistant", "content": assistant_response})

        # Trim context window: keep system prompt + last 10 messages
        if len(chat_histories[session_id]) > 12:
            chat_histories[session_id] = (
                [chat_histories[session_id][0]] + chat_histories[session_id][-10:]
            )

        return json.dumps({"content": assistant_response})

    except Exception as e:
        print(f"Error in chat_response: {e}")
        # Always return valid JSON so the client can parse the response
        return json.dumps({"content": "I'm experiencing a technical issue. Could you please repeat that?"})

    finally:
        if ka_task:
            ka_task.cancel()


async def handle_websocket(websocket, path):
    session_id = id(websocket)
    try:
        await websocket.send(json.dumps({"content": "Hi! How can I help you today?"}))
        async for message in websocket:
            content = json.loads(message).get("content", "")
            if not content:
                continue  # skip metadata-only frames
            print(f"Received: {content}")
            response = await chat_response(content, session_id, websocket=websocket)
            await websocket.send(response)
            print(f"Sent: {response}")

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        chat_histories.pop(session_id, None)


async def main():
    port = int(os.environ.get("PORT", 8765))
    server = await websockets.serve(
        handle_websocket,
        "0.0.0.0",
        port,
        ping_interval=None,  # Disable server->client pings; let the client manage keepalive.
                              # Our application-level keepalive (every 8s) handles liveness.
    )
    print(f"WebSocket server started on ws://0.0.0.0:{port}")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
