import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

MODEL = "gemini-3.1-flash-lite"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL,
        api_key=GEMINI_API_KEY,
        request_timeout=90,
        max_retries=2,
    )

if __name__ == "__main__":
    model = get_model()

    print(model.invoke("Are you onlne?"))