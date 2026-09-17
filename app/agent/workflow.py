from langchain_core.messages import (
    HumanMessage, SystemMessage, AnyMessage
)
from typing import Literal, Annotated, Callable
from pydantic import Field, BaseModel

import re
import asyncio

from app.services.sheets_service import upsert_to_sheet
from app.agent.model import get_model
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from app.services.gmail_mcp import get_google_mcp_tools
from app.services.mcp_server import save_processed_ids
from app.logger import get_logger

logger = get_logger("agent.workflow")

# Application Status Accepted Literal
ApplicationStatus = Literal["applied", "viewed", "interview", "rejected", "accepted"]

# Sheet model - represents a single row of a sheet
class SheetModel(BaseModel):
    company_name: str | None = Field(default=None, description="the name of the company the user applied to")
    job_title: str | None = Field(default=None, description="the job title the user applied for")
    location: str | None = Field(default=None, description="the location of the job applied for")
    status: ApplicationStatus | None = Field(default=None, description="the status of the application")
    date: str | None = Field(default=None, description="the date of the application or status update in YYYY-MM-DD format")
    short_summary: str | None = Field(default=None, description="short summary of the email")


# Build States
class ExtractedResult(BaseModel):
    updates: list[SheetModel] = Field(description="a list of all job applications updates found in the emails") 

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


class AgentState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    final_output: list[SheetModel] = Field(default_factory=list)
    fetched_message_ids: list[str] = Field(default_factory=list)
    sync_report: dict = Field(default_factory=dict)


# Graph Factory

def create_graph(tools, progress_callback: Callable[[str, int], None] | None = None):
    """Factory function that builds the graph with the provided tools and progress callback."""
    llm_with_tools = get_model().bind_tools(tools)
    tool_node = ToolNode(tools) # node 0: tools

    # nodes 1: fetch email
    async def get_email(state: AgentState) -> dict:
        logger.info("Executing node 'get_email' - querying LLM to call email tool.")
        if progress_callback:
            progress_callback("Querying recent emails from Gmail inbox...", 1)
        messages = state.messages
        # The LLM decides whether to call a tool or reply to the user
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # node 2: analyze fetched email/s
    async def analyze_email(state: AgentState) -> dict:
        logger.info("Executing node 'analyze_email' - parsing emails for job updates.")
        if progress_callback:
            progress_callback("Analyzing emails with GenAI for job updates...", 1)
            
        raw_content = state.messages[-1].content
        if isinstance(raw_content, list):
            texts = [b["text"] if isinstance(b, dict) and "text" in b else str(b) for b in raw_content]
            last_message = "\n".join(texts)
        else:
            last_message = str(raw_content)
        
        # Extract fetched message IDs safely
        message_ids = extract_message_ids(raw_content)
        logger.info("Identified %d fetched email message ID(s) in tool output.", len(message_ids))
        
        if "No job updates found" in last_message or last_message.strip() in ("", "[]"):
            logger.info("No email updates found in tool output.")
            if message_ids:
                save_processed_ids(message_ids)
            return {"final_output": [], "fetched_message_ids": message_ids}
                
        # Extract the structured data from the raw tool output or LLM summary
        structured_llm = llm_with_tools.with_structured_output(ExtractedResult)
        
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
            # All fetched emails were analyzed and contained no valid job updates; safe to mark processed
            save_processed_ids(message_ids)
            
        return {"final_output": response.updates, "fetched_message_ids": message_ids}
    
    # node 3: update the google sheets
    async def update_sheets(state: AgentState) -> dict:
        updates = state.final_output
        logger.info("Executing node 'update_sheets' with %d update(s).", len(updates) if updates else 0)
        if progress_callback:
            progress_callback("Syncing updates to Google Sheets...", 1)
            
        if not updates:
            logger.info("No updates to sync to Google Sheets.")
            return {"sync_report": {"appended": [], "updated": [], "skipped": []}}
            
        rows = []
        for model in updates:
            rows.append([
                model.company_name or "",
                model.job_title or "",
                model.location or "",
                model.status or "",
                model.date or "",
                model.short_summary or ""
            ])
            
        # Call our service synchronously in a background thread to not block event loop
        report = await asyncio.to_thread(upsert_to_sheet, rows)
        logger.info("Google Sheets upsert completed successfully.")

        # Atomic commit: Only mark message IDs as processed once sheet updates succeed!
        if state.fetched_message_ids:
            save_processed_ids(state.fetched_message_ids)
        return {"sync_report": report or {}}

    # --- Build the Graph ---
    workflow = StateGraph(AgentState)
    workflow.add_node("get_email", get_email)
    workflow.add_node("tools", tool_node)
    workflow.add_node("analyzer", analyze_email)
    workflow.add_node("update_sheets", update_sheets)
    workflow.add_edge(START, "get_email")

    workflow.add_conditional_edges(
        "get_email", 
        tools_condition, 
        {"tools": "tools", "__end__": "analyzer"}
    )

    workflow.add_edge("tools", "analyzer")
    workflow.add_edge("analyzer", "update_sheets")
    workflow.add_edge("update_sheets", END)
    return workflow.compile()


async def run_agent(progress_callback: Callable[[str, int], None] | None = None, days_ago: int = 7):
    """Encapsulates the graph building and MCP tool context."""
    logger.info("Initializing run_agent workflow (days_ago=%d).", days_ago)
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