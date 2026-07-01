from langchain_core.messages import AIMessage
from typing import Literal, Annotated
from pydantic import Field, BaseModel
from app.agent.llm import model
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages



# state
class InputState(BaseModel):
    raw_email: str

    
class OutputState(BaseModel):
    company_name: str | None = Field(default=None, description="the name of the company the user applied")
    job_title: str | None = Field(default=None, description="the job title the user applied")
    location: str | None =  Field(default=None, description="the location of the job applied")
    status: Literal["applied", "viewed", "interview", "rejected", "accepted"] | None = Field(default=None, description="the status of the application")
    short_summary: str | None = Field(default=None, description="short summary of the email")

class AgentState(InputState, OutputState):
    messages: Annotated[list[str], add_messages]

# nodes
def get_email(state: InputState) -> AgentState:
    
    # TODO: add mechanism later for getting the email from the gmail API
    email = """
    LinkedIn <jobs-noreply@linkedin.com> Unsubscribe
    Tue, Jun 23, 7:41 PM (8 days ago)
    to me

    Your update from Watermelon Software Inc

    AI Engineer (0–3 Years) - ManilaWatermelon Software Inc · Manila, National Capital Region, Philippines

    Applied on Jun 20

    Thank you for your interest in the AI Engineer (0–3 Years) - Manila position at Watermelon Software Inc in Manila, National Capital Region, Philippines. Unfortunately, we will not be moving forward with your application, but we appreciate your time and interest in Watermelon Software Inc.

    Regards,

    Watermelon Software Inc
    """
    # raw_email = InputState(raw_email="")
    return {
       "raw_email": email
    }

def analyze_email(state: AgentState) -> OutputState:
    structured_llm = model.with_structured_output(OutputState)
    
    response: OutputState = structured_llm.invoke(state.raw_email)

    return {
        "company_name": response.company_name,
        "job_title": response.job_title,
        "location": response.location,
        "status": response.status,
        "short_summary": response.short_summary
    }

def update_sheet():
    pass



# Compile Graph


def compile_graph():
    workflow = StateGraph(AgentState, input_schema=InputState, output_schema=OutputState)

    workflow.add_node("get_email", get_email)
    workflow.add_node("analyzer", analyze_email)

    # TODO: add the update sheet


    workflow.add_edge(START, "get_email")
    workflow.add_edge("get_email", "analyzer")
    workflow.add_edge("analyzer", END)

    return workflow.compile()


if __name__ == "__main__":
    app = compile_graph()

    import pprint
    # import os
    # from IPython.display import Image, display
    # output_path = os.path.join(os.path.dirname(__file__), "graph.png")

    # with open(output_path, "wb") as f:
    #         # Call the method with () and write the bytes directly to the file
    #         f.write(app.get_graph().draw_mermaid_png())
    

    # test code

    initial_state = {
        "raw_email": "",
    } 


    print("Start workflow")

    print("worflow running")
    result = app.invoke(initial_state)

    print("end workflow")

    pprint.pprint(result)

    