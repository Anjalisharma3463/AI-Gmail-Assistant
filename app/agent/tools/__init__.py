from langchain.tools import tool
import requests
from pydantic import BaseModel, Field

API_BASE_URL = "http://localhost:8000"  # Replace with deployed URL if needed

# ----------------------
# Read Email Tool
# ----------------------
class ReadEmailInput(BaseModel):
    user_query: str = Field(..., description="A natural language query to find specific emails. Example: 'Give me Unread emails from yesterday' , 'show me today's mails'")

@tool(args_schema=ReadEmailInput)
def read_email_tool(user_query: str) -> list:
    """Get emails based on natural language query using Gmail filters."""
    response = requests.post(f"{API_BASE_URL}/read_email", json={"user_query": user_query})
    return response.json()

# ----------------------
# Generate Draft Tool
# ----------------------
class GenerateDraftInput(BaseModel):
    prompt: str = Field(..., description="The user's email intent, e.g., 'Send email to Mohit about the joining date', 'Reply to the email from Anjali about the project status'")
    original_email: dict = Field(None, description="Original email object if replying")

@tool(args_schema=GenerateDraftInput)
def generate_draft_tool(prompt: str, original_email: dict = None) -> dict:
    """
    Create a draft email based on prompt. Determines action: 'new' or 'reply'.
    If it's a reply, fetch original email using read_email_tool.
    """
    is_reply = any(word in prompt.lower() for word in ["reply", "respond", "answer"])
    payload = {"prompt": prompt, "action": "reply" if is_reply else "new"}

    if is_reply:
        read_response = requests.post(f"{API_BASE_URL}/read_email", json={"user_query": prompt})
        try:
            emails = read_response.json()
        except Exception:
            return {"error": "Failed to parse read_email response."}

        if not emails:
            return {"error": "No matching email found to reply to."}

        payload["original_email"] = emails[0]

    response = requests.post(f"{API_BASE_URL}/generate-draft-email", json=payload)
    return response.json()

# ----------------------
# Summarize Tool
# ----------------------
class SummarizeInput(BaseModel):
    prompt: str = Field(..., description="User's query, like 'Summarize unread emails from HR this week'")

@tool(args_schema=SummarizeInput)
def summarize_tool(prompt: str) -> str:
    """Auto-summarizes one or more emails based on a query."""
    read_result = requests.post("http://localhost:8000/read_emails", json={"user_query": prompt})
    emails = read_result.json().get("emails", [])

    if not emails:
        return "No emails found to summarize."

    summarize_result = requests.post("http://localhost:8000/summarize", json={"emails": emails})
    summaries = summarize_result.json().get("summaries", [])
    
    return "\n\n".join(f"- {email['summary']}" for email in summaries)