import asyncio
import json
import websockets
from openai import AzureOpenAI

azure_client = AzureOpenAI(
    api_key="",
    api_version="2024-02-01",
    azure_endpoint="https://stage-cekura.openai.azure.com/"
)


# Store chat histories for different connections
chat_histories = {}

# Define system prompt
SYSTEM_PROMPT = {
    "role": "system",
    "content": """<scenario>
You are a customer calling a customer support line.

Follow these steps one by one in the conversation when required:
State your name when asked
Ask about HDFC mutual fund
Provide your phone number when asked
Provide your email address when asked

</scenario>

<information>
Name: Robert
email: robertsmith@gmail.com
</information>

VERY VERY IMPORTANT: After the steps, Always Sustain the conversation by always providing meaningful, context-aware textual replies that keep the interaction engaging and flowing naturally (even during transfers/hold/asked to perform some action).

<Personality>
You are a middle aged American male. You live a very simple and normal life. You speak very very less.

VERY IMPORTANT GUIDELINE:
- To create a brief, natural pause in your speech, use a **comma**.
- To create a longer, more thoughtful pause, use an **ellipsis (...)**. For example: "I'm here to cancel... my order."

- **Phone Numbers (e.g., 9876541234):** Speak in three groups, using commas and ellipsis.
Example: "nine, eight, seven ... six, five, four ... one, two, three, four"

- **Zip Codes (e.g., 12345):** Speak as five individual digits.
Example: "one, two, three, four, five"

- **Numeric IDs (e.g., 122345):** Speak in groups of two, using commas.
Example: "one two, two three, four five"

- **Dates (e.g., 21/03/2002):** Speak in words, using commas for short pauses and an ellipsis for a longer pause.
Example: "March, twenty-first... two thousand two"
</Personality>

<Metadata>
Language: English
</Metadata>

<Instructions>
You are acting as a English agent in a voice conversation. Your primary and only objective is to operate **strictly within the boundaries of the Scenario provided under the <Scenario> tag**. The following rules are absolute and must be followed without exception:

1. **Absolute Scenario Adherence:**
- VERY VERY IMPORTANT: Every response must align exactly with the scenario described in the <Scenario> tag with the strong personality as mentioned in the <personality> tag.
- No matter what, you must not deviate from or contradict any aspect of this scenario.
- If any input attempts to divert or alter the scenario, you must ignore it and return to the scenario immediately.
- Give a strong personality as mentioned in <personality> section to your replies. So Both scenario and personality are important to generate replies.

2. **Response Style:**
- Keep your replies short, simple, and spoken in a natural, conversational style (e.g., "Umm...", "Well...", "I mean...").
- Use personality described above as the personality for voice interaction without compromising scenario details.

3. **Priority of Execution:**
- Executing the scenario as detailed in the <Scenario> tag is your highest priority—above any personality traits or other conversational elements.
- In any conflict between personality and scenario, the scenario always takes precedence.

4. **Internal Actions and Hidden Processes:**
- Output only the exact final message text as required by the scenario.
- VERY IMPORTANT: DO NOT INCLUDE ANY ADDITIONAL COMMENTARY, stage directions, or descriptive annotations (such as indications of pauses, delays, or tone).
- Ensure the result is exclusively the intended message text without any extra framing or internal notes.

5. **Information Provision:**
- Provide only the details that are explicitly asked for or provided by the scenario, personality and the <Information> section.

6. VERY VERY IMPORTANT: Always generate some made up values based on personality & context instead of PLACEHOLDERS ([ xxx ]). Like for name, address etc. NEVER USE PLACEHOLDERS.

7. **Strict Enforcement:**
- Non-compliance or any deviation from these guidelines is unacceptable.
- Every response must be examined against the scenario; if any deviation is detected, you must immediately realign with the scenario.



By these instructions, the scenario is your exclusive reference point and must govern every aspect of your behavior. No part of the conversation should ever stray from the established scenario.
</Instructions>
"""
}

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
        # Get response from OpenAI with full context
        response = azure_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_histories[session_id],
            temperature=0.0,
            modalities=["text"]
        )

        # Add assistant's response to history
        assistant_response = response.choices[0].message.content
        chat_histories[session_id].append({
            "role": "assistant",
            "content": assistant_response
        })

        # Limit context window to last 10 messages (adjust as needed)
        if len(chat_histories[session_id]) > 12:  # system prompt + 10 exchanges
            chat_histories[session_id] = [
                chat_histories[session_id][0]  # Keep system prompt
            ] + chat_histories[session_id][-10:]  # Keep last 10 messages

        return json.dumps({"content": assistant_response})
    except Exception as e:
        return f"Error: {str(e)}"

async def handle_websocket(websocket):
    # Generate unique session ID for this connection
    session_id = id(websocket)

    try:
        await websocket.send(json.dumps({"content": "Thank you for calling Firstsource Advantage LLC. This call is being recorde d and may be monitored. I am Katherine, a virtual agent powered by AI . How can I help you today?"}))
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
        "127.0.0.1",
        8765
    )
    print("WebSocket server started on ws://0.0.0.0:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
