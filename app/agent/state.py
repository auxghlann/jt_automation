from typing import Literal, Annotated
from pydantic import Field, BaseModel
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

# Application Status Accepted Literal
ApplicationStatus = Literal["applied", "viewed", "interview", "rejected", "accepted"]

# Helper State
class SheetModel(BaseModel):
    """Represents a single row of a sheet."""
    company_name: str | None = Field(default=None, description="the name of the company the user applied to")
    job_title: str | None = Field(default=None, description="the job title the user applied for")
    location: str | None = Field(default=None, description="the location of the job applied for")
    status: ApplicationStatus | None = Field(default=None, description="the status of the application")
    date: str | None = Field(default=None, description="the date of the application or status update in YYYY-MM-DD format")
    short_summary: str | None = Field(default=None, description="short summary of the email")


# Agent States
class ExtractedResult(BaseModel):
    """Container for batch-extracted job updates."""
    updates: list[SheetModel] = Field(description="a list of all job applications updates found in the emails")


class AgentState(BaseModel):
    """Workflow state container passed across LangGraph nodes."""
    messages: Annotated[list[AnyMessage], add_messages]
    final_output: list[SheetModel] = Field(default_factory=list)
    fetched_message_ids: list[str] = Field(default_factory=list)
    sync_report: dict = Field(default_factory=dict)
