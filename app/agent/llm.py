import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

groq_api_key = os.environ.get("GROQ_API_KEY")

system_promt = SystemMessage(
    content="""
    You are an AI assistant. You MUST start by calling the get_recent_emails tool. Do not generate any other text until you have called the tool and received its output.
    """
)

smart_model = ChatGroq(
    model = "llama-3.3-70b-versatile",
    temperature = 0
)

fast_model = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
)

if __name__ == "__main__":

    messages = [
        HumanMessage(content="System Check: Are you online?")
    ]
    
    print("fast model response")
    response = fast_model.invoke(messages)
    print(response.content)

    print("smart model response")
    response2 = smart_model.invoke(messages)
    print(response2)