from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter()

@router.post("/generate_query")
async def generate_gmail_query(user_input: str):
    try:
        if not user_input:
            return JSONResponse(content={"error": "No user input provided"}, status_code=400)

        # Define Gemini prompt
        today = datetime.utcnow().strftime("%Y/%m/%d")
        prompt = f"""
You are an expert assistant that converts natural language into Gmail search queries using Gmail's search operators.

Supported search operators include:
- from:, to:, subject:, after:, before:, has:attachment, is:unread, etc.

Today's date is {today}.
DO NOT explain anything, just return the Gmail search query based on this user input:

User input: "{user_input}"

Gmail query:
"""

        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            contents=[prompt],
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=80,
            )
        )

        query = response.text.strip()
        print("Gemini Gmail query:", query)

        return {"gmail_query": query}

    except Exception as e:
        print("Gemini error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
