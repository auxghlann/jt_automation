import asyncio
from typing import Callable
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.google_auth import get_credentials
from app.services.gmail_mcp import get_google_mcp_tools
from app.agent.workflow import create_graph
from app.logger import get_logger

logger = get_logger("services.agent")


async def run_agent(progress_callback: Callable[[str, int], None] | None = None, days_ago: int = 7):
    """Encapsulates graph building, pre-flight auth, and MCP tool context."""
    logger.info("Initializing run_agent workflow (days_ago=%d).", days_ago)
    if progress_callback:
        progress_callback("Verifying Google credentials...", 0)
    await asyncio.to_thread(get_credentials, interactive=False)

    if progress_callback:
        progress_callback("Connecting to Gmail MCP server...", 0)

    async with get_google_mcp_tools() as tools:
        logger.info("Retrieved %d tools from Gmail MCP server.", len(tools))
        if progress_callback:
            progress_callback("Connected to Gmail MCP server.", 1)

        app = create_graph(tools, progress_callback=progress_callback)

        initial_state = {
            "messages": [
                SystemMessage(
                    "You are an AI job application assistant. You MUST use the `get_recent_emails` tool immediately to fetch emails. "
                    "Do not apologize or say you don't have access. Call the tool first. "
                    "After you receive the tool's output, read through the emails and identify any job updates. "
                    "If none are found, reply with 'No job updates found'."
                ),
                HumanMessage(
                    f"Please check my recent emails from the last {days_ago} days for job updates."
                )
            ]
        }

        logger.info("Invoking LangGraph workflow with initial state.")
        result = await app.ainvoke(initial_state)
        logger.info("LangGraph workflow execution finished.")
        return result
