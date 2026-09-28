import re
import asyncio
from typing import Callable

from langgraph.prebuilt import ToolNode
from app.agent.state import AgentState, ExtractedResult
from app.agent.model import get_model
from app.services.sheets_service import upsert_to_sheet
from app.services.mcp_server import save_processed_ids
from app.logger import get_logger

logger = get_logger("agent.nodes")


def extract_message_ids(raw_content) -> list[str]:
    """Safely extracts message IDs from tool output regardless of format or escaping."""
    text_blocks = []
    if isinstance(raw_content, list):
        for item in raw_content:
            if isinstance(item, dict) and "text" in item:
                text_blocks.append(str(item["text"]))
            else:
                text_blocks.append(str(item))
    else:
        text_blocks.append(str(raw_content))

    combined_text = "\n".join(text_blocks)
    ids = re.findall(r"message_id['\"\\]*\s*:\s*['\"\\]*([a-zA-Z0-9_\-]+)", combined_text)
    return list(dict.fromkeys(ids))


class WorkflowNodes:
    """Encapsulates node execution logic for the job tracker agent."""

    def __init__(
        self,
        tools: list,
        progress_callback: Callable[[str, int], None] | None = None,
        llm_with_tools=None
    ):
        self.tools = tools
        self.progress_callback = progress_callback
        self.llm_with_tools = llm_with_tools if llm_with_tools is not None else get_model().bind_tools(tools)
        self.tool_node = ToolNode(tools)

    async def get_email(self, state: AgentState) -> dict:
        """Node 1: Calls the LLM to trigger email-fetching tools."""
        logger.info("Executing node 'get_email' - querying LLM to call email tool.")
        if self.progress_callback:
            self.progress_callback("Querying recent emails from Gmail inbox...", 1)
        messages = state.messages
        response = await self.llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    async def analyze_email(self, state: AgentState) -> dict:
        """Node 2: Analyzes fetched emails and performs structured extraction of job updates."""
        logger.info("Executing node 'analyze_email' - parsing emails for job updates.")
        if self.progress_callback:
            self.progress_callback("Analyzing emails with GenAI for job updates...", 1)

        raw_content = state.messages[-1].content
        if isinstance(raw_content, list):
            texts = [b["text"] if isinstance(b, dict) and "text" in b else str(b) for b in raw_content]
            last_message = "\n".join(texts)
        else:
            last_message = str(raw_content)

        message_ids = extract_message_ids(raw_content)
        logger.info("Identified %d fetched email message ID(s) in tool output.", len(message_ids))

        if "No job updates found" in last_message or last_message.strip() in ("", "[]"):
            logger.info("No email updates found in tool output.")
            if message_ids:
                save_processed_ids(message_ids)
            return {"final_output": [], "fetched_message_ids": message_ids}

        structured_llm = self.llm_with_tools.with_structured_output(ExtractedResult)
        prompt = (
            "Analyze these emails and extract ONLY the job updates where the application status "
            "is EXACTLY one of or in the CONTEXT of: 'applied', 'viewed', 'interview', 'rejected', 'accepted'. "
            "Extract the date of the email/event in 'YYYY-MM-DD' format into the date field. "
            "Completely IGNORE any emails about 'saved' jobs, 'expired' jobs, or any other irrelevant statuses. "
            f"Emails: {last_message}"
        )
        response: ExtractedResult = await structured_llm.ainvoke(prompt)
        logger.info("Structured extraction completed: %d updates found.", len(response.updates))

        if not response.updates and message_ids:
            save_processed_ids(message_ids)

        return {"final_output": response.updates, "fetched_message_ids": message_ids}

    async def update_sheets(self, state: AgentState) -> dict:
        """Node 3: Syncs extracted application updates to Google Sheets."""
        updates = state.final_output
        logger.info("Executing node 'update_sheets' with %d update(s).", len(updates) if updates else 0)
        if self.progress_callback:
            self.progress_callback("Syncing updates to Google Sheets...", 1)

        if not updates:
            logger.info("No updates to sync to Google Sheets.")
            return {"sync_report": {"appended": [], "updated": [], "skipped": []}}

        rows = [
            [
                model.company_name or "",
                model.job_title or "",
                model.location or "",
                model.status or "",
                model.date or "",
                model.short_summary or ""
            ]
            for model in updates
        ]

        report = await asyncio.to_thread(upsert_to_sheet, rows)
        logger.info("Google Sheets upsert completed successfully.")

        if state.fetched_message_ids:
            save_processed_ids(state.fetched_message_ids)
        return {"sync_report": report or {}}
