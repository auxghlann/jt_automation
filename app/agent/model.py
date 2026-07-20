import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

MODEL = "gemma-4-31b-it"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

model = ChatGoogleGenerativeAI(
    model=MODEL,
    api_key=GEMINI_API_KEY
)

if __name__ == "__main__":

    system_promt = SystemMessage(
    content="""
    You are an AI assistant. You MUST start by calling the get_recent_emails tool. Do not generate any other text until you have called the tool and received its output.
    """
    )

    messages = [
        HumanMessage(content="System Check: Are you online?")
    ]

    print("gemma model")
    response = model.invoke(messages)
    print(response.content)