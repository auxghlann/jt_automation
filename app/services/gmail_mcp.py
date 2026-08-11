import sys
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools

from app.errors.exceptions import AuthRequiredError

# Sentinel strings the MCP server serializes when Google auth fails.
# This is the single place to update if the wording ever changes.
AUTH_ERROR_MESSAGES = (
    "Google authentication is required",
    "Google authentication token is expired",
)


def _is_auth_error_text(text: str) -> bool:
    return any(msg in text for msg in AUTH_ERROR_MESSAGES)


def _raise_if_auth_error(result) -> None:
    """Inspect an MCP tool result and raise AuthRequiredError if it signals an auth failure."""
    content = result[0] if isinstance(result, tuple) else result

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                if _is_auth_error_text(block.get("text", "")):
                    raise AuthRequiredError("Google authentication is required.")
    elif isinstance(content, str):
        if _is_auth_error_text(content):
            raise AuthRequiredError("Google authentication is required.")


def _wrap_tool_for_auth_errors(tool):
    """Wraps a LangChain MCP tool so that authentication failures raise AuthRequiredError."""
    original_coroutine = tool.coroutine

    async def wrapped_coroutine(*args, **kwargs):
        try:
            result = await original_coroutine(*args, **kwargs)
        except Exception as exc:
            if _is_auth_error_text(str(exc)):
                raise AuthRequiredError("Google authentication is required.") from exc
            raise

        _raise_if_auth_error(result)
        return result

    # Prevent LangChain's handle_tool_error from swallowing AuthRequiredError.
    original_handler = getattr(tool, "handle_tool_error", None)

    def wrapped_handler(error: Exception) -> str:
        if isinstance(error, AuthRequiredError):
            raise error
        if callable(original_handler):
            return original_handler(error)
        if original_handler is True:
            return f"Error executing tool: {error}"
        raise error

    tool.coroutine = wrapped_coroutine
    tool.handle_tool_error = wrapped_handler
    return tool


@asynccontextmanager
async def get_google_mcp_tools():
    """Connects to the local FastMCP server via stdio and yields LangChain tools."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.services.mcp_server"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            wrapped_tools = [_wrap_tool_for_auth_errors(t) for t in tools]
            yield wrapped_tools
