from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from .tools import (
    read_email_tool,
    generate_draft_tool,
    summarize_tool
)
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",  # or "gemini-2.0-flash"
    google_api_key=GEMINI_API_KEY,
    temperature=0.3
)

def get_agent():
    tools = [
        read_email_tool,
        generate_draft_tool, 
        summarize_tool
    ]

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,  # Gemini supports this tool format
        verbose=True,
        handle_parsing_errors=True
    )
    return agent
