from langchain_core.messages import (
    AIMessage, SystemMessage, AnyMessage, RemoveMessage
)
from typing import Literal, Annotated
from pydantic import Field, BaseModel
from operator import add

from app.services.sheets_service import upsert_to_sheet
from app.agent.llm import fast_model, smart_model
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from app.services.gmail_mcp import get_google_mcp_tools


import asyncio

# Sheet model - represents a single row of a sheet
class SheetModel(BaseModel):
    company_name: str | None = Field(default=None, description="the name of the company the user applied")
    job_title: str | None = Field(default=None, description="the job title the user applied")
    location: str | None =  Field(default=None, description="the location of the job applied")
    status: Literal["applied", "viewed", "interview", "rejected", "accepted"] | None = Field(default=None, description="the status of the application")
    short_summary: str | None = Field(default=None, description="short summary of the email")


# Build States
class ExtractedResult(BaseModel):
    updates: list[SheetModel] = Field(description="a list of all job applications updates found in the emails") 

class AgentState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    final_output: Annotated[list[SheetModel], add]


# Graph Factory

def create_graph(tools):
    """Factory function that builds the graph with the provided tools."""
    llm_with_tools = fast_model.bind_tools(tools)
    tool_node = ToolNode(tools) # node 0: tools

    # nodes 1: fetch email
    async def get_email(state: AgentState) -> dict:
        messages = state.messages
        
        if len(messages) > 3:
            recent_message = [RemoveMessage(id=m.id) for m in messages[1:-1]]
            return {"messages": recent_message}
        
        if not messages:
            # First run: give the LLM its instructions
            messages = [
                SystemMessage(
                    "You are an AI job application assistant. You MUST use the `get_recent_emails` tool immediately to fetch emails. "
                    "Do not apologize or say you don't have access. Call the tool first. "
                    "After you receive the tool's output, read through the emails and identify any job updates. "
                    "If none are found, reply with 'No job updates found'."
                )
            ]
            
        # The LLM decides whether to call a tool or reply to the user
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # node 2: analyze fetched email/s
    async def analyze_email(state: AgentState) -> dict:
        raw_content = state.messages[-1].content

        last_message = str(raw_content)
        
        if "No job updates found" in last_message or last_message == "[]":
                return {"final_output": None}
                
        # Extract the structured data from the raw tool output or LLM summary
        structured_llm = smart_model.with_structured_output(ExtractedResult)
        
        # --- NEW: Instruct the smart model directly! ---
        prompt = (
            "Analyze these emails and extract ONLY the job updates where the application status "
            "is EXACTLY one of or in the CONTEXT of: 'applied', 'viewed', 'interview', 'rejected', 'accepted'. "
            "Completely IGNORE any emails about 'saved' jobs, 'expired' jobs, or any other irrelevant statuses. "
            f"Emails: {last_message}"
        )
        response: ExtractedResult = await structured_llm.ainvoke(prompt)
        
        return {"final_output": response.updates}
    
    # node 3: update the google sheets
    async def update_sheets(state: AgentState) -> dict:
        updates = state.final_output
        if not updates:
            print("No updates to push to Google Sheets.")
            return {}
            
        print(f"Checking {len(updates)} updates against Google Sheets...")
        
        rows = []
        for model in updates:
            rows.append([
                model.company_name or "",
                model.job_title or "",
                model.location or "",
                model.status or "",
                model.short_summary or ""
            ])
            
        # Call our new service
        upsert_to_sheet(rows)
        return {}

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


if __name__ == "__main__":
    import pprint
    
    # async def get_graph_image():
    #     async with get_google_mcp_tools() as tools:
    #         print("Server connected. Building graph...")
    #         app = create_graph(tools)

    #     import os
    #     from IPython.display import Image, display
    #     output_path = os.path.join(os.path.dirname(__file__), "graph.png")

    #     with open(output_path, "wb") as f:
    #             # Call the method with () and write the bytes directly to the file
    #             f.write(app.get_graph().draw_mermaid_png())
    
    # asyncio.run(get_graph_image())
        

    
    # test code
    async def run_test():
        print("Connecting to local MCP server...")
        
        # Keep the connection alive while the graph runs!
        async with get_google_mcp_tools() as tools:
            print("Server connected. Building graph...")
            app = create_graph(tools)
            initial_state = {"messages": []} 
            
            print("Running workflow...")
            result = await app.ainvoke(initial_state)
            
            print("\n--- Final Output ---")
            pprint.pprint(result)
    asyncio.run(run_test())

    