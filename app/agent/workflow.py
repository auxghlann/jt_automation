from typing import Callable

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition
from app.agent.state import AgentState
from app.agent.nodes import WorkflowNodes
from app.agent.model import get_model


def create_graph(tools, progress_callback: Callable[[str, int], None] | None = None):
    """Factory function that builds the LangGraph state graph with provided tools and progress callback."""
    nodes = WorkflowNodes(
        tools=tools,
        progress_callback=progress_callback,
        llm_with_tools=get_model().bind_tools(tools)
    )

    workflow = StateGraph(AgentState)
    workflow.add_node("get_email", nodes.get_email)
    workflow.add_node("tools", nodes.tool_node)
    workflow.add_node("analyzer", nodes.analyze_email)
    workflow.add_node("update_sheets", nodes.update_sheets)

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