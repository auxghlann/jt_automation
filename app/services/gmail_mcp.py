import sys
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools

@asynccontextmanager
async def get_google_mcp_tools():
    """Connects to the local FastMCP server via stdio and yields LangChain tools."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.services.mcp_server"],
        env=None
    )

    # Connect to the local subprocess
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            yield tools

