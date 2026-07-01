import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

groq_api_key = os.environ.get("GROQ_API_KEY")

system_promt = SystemMessage(
    content="""
    You are a helpful assistant managaming my emails from my job application
    """
)

model = ChatGroq(
    model = "meta-llama/llama-4-scout-17b-16e-instruct",
    temperature = 0.5
)

if __name__ == "__main__":

    messages = [
        HumanMessage(content="System Check: Are you online?")
    ]
        
    response = model.invoke(messages)
    print(response.content)