import asyncio, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    here = os.path.dirname(os.path.abspath(__file__))
    params = StdioServerParameters(command=sys.executable,
                                   args=[os.path.join(here, "metro_server.py")])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for t in tools.tools:
                print("TOOL:", t.name, "\n", t.description, "\n")
            result = await session.call_tool("get_next_buses",
                                             {"direction": "toward_downtown", "limit": 3})
            for block in result.content:
                print("RESULT:", block.text)

asyncio.run(main())