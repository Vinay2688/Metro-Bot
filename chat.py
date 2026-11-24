import asyncio, json, os, sys
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-120b"        # keep whichever model name worked for you before

SYSTEM = (
    "You are a bus assistant for University of Cincinnati students, using live "
    "Cincinnati Metro data. For any question about bus times, ALWAYS call the "
    "get_next_buses tool; never guess times. Bus data changes every minute, so "
    "call the tools again for every such question and never reuse numbers from "
    "earlier in the conversation. Always say which direction each bus is going. "
    "To explain where a route goes, call get_route_info and report the "
    "destination for EACH direction. To say where buses are right now, call "
    "get_bus_locations and describe each position as 'near' a stop, naming the "
    "bus's destination; mention if a position is more than 2 minutes old. Never "
    "describe routes from memory. get_next_buses only covers the stop at "
    "Jefferson Ave & University Ave on the UC campus. You do not know the user's "
    "location and cannot find other stops. Only state facts that come from tool "
    "results. Answer briefly. If asked about something unrelated to buses, "
    "answer normally without tools."
)

async def main():
    here = os.path.dirname(os.path.abspath(__file__))
    params = StdioServerParameters(command=sys.executable,
                                   args=[os.path.join(here, "metro_server.py")])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Ask the MCP server for its tools and convert them to OpenAI's format
            mcp_tools = (await session.list_tools()).tools
            tools = [{
                "type": "function",
                "function": {"name": t.name, "description": t.description,
                             "parameters": t.input_schema},
            } for t in mcp_tools]
            print("Connected. Tools:", [t.name for t in mcp_tools])
            print("Ask about buses. Type 'quit' to exit.\n")

            messages = [{"role": "system", "content": SYSTEM}]

            while True:
                user = input("You: ").strip()
                if user.lower() in {"quit", "exit"}:
                    break

                # Refresh the clock on every question so the time is never stale
                now = datetime.now().strftime("%A %I:%M %p")
                messages[0]["content"] = SYSTEM + f" The current local time is {now}."

                checkpoint = len(messages)
                messages.append({"role": "user", "content": user})
                try:
                    for _ in range(5):                       # max 5 tool rounds per question
                        resp = client.chat.completions.create(
                            model=MODEL, messages=messages, tools=tools)
                        msg = resp.choices[0].message
                        if not msg.tool_calls:               # plain answer: we're done
                            messages.append({"role": "assistant", "content": msg.content})
                            print("Bot:", msg.content, "\n")
                            break
                        # The LLM wants tools: record its request, run each, send results back
                        messages.append({
                            "role": "assistant", "content": msg.content,
                            "tool_calls": [{"id": tc.id, "type": "function",
                                            "function": {"name": tc.function.name,
                                                         "arguments": tc.function.arguments}}
                                           for tc in msg.tool_calls],
                        })
                        for tc in msg.tool_calls:
                            args = json.loads(tc.function.arguments or "{}")
                            print(f"  [calling tool {tc.function.name} {args}]")
                            result = await session.call_tool(tc.function.name, args)
                            text = "\n".join(b.text for b in result.content if hasattr(b, "text"))
                            messages.append({"role": "tool", "tool_call_id": tc.id,
                                             "content": text})
                    else:
                        print("Bot: (stopped after too many tool rounds)\n")
                except OpenAIError as e:
                    print("Error:", e, "\n")
                    del messages[checkpoint:]                # drop the failed turn

asyncio.run(main())