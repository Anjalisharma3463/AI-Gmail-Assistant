# {
#   "action": "send" | "reply" | "summarize" | "search",
#   "needs_email_content": true | false
# }
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import google.generativeai as genai
import os, re
import json
load_dotenv(".env.production")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter()



@router.post("/classify_query")
async def classify_query(request: Request):
    try:
        user = request.state.user
        username = user["username"]
        logged_in_email = user["email"]

        data = await request.json()

        user_query = data["query"].strip()
        if not user_query:
            return JSONResponse(content={"error": "Query cannot be empty."}, status_code=400)
        
        prompt = (
                    f"""
        You are an AI assistant. Your job is to understand what the user wants to do with their email. 
        
        Classify the following prompt into one of the following actions:
        - "send": User wants to send a new email
        - "reply": User wants to reply to someone
        - "summarize": User wants to summarize email(s)
        - "search": User wants to find emails, no summarizing or replying
        
        Respond in JSON like:
        {{ "action": "...", "needs_email_content": true/false }}
        
        User Prompt: "{{user_query}}"
        """
                )

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            contents=[prompt],
            generation_config=genai.GenerationConfig(
                max_output_tokens=100,
                temperature=0.7
            )
        )
        response_text = response.text.strip()   
        if not response_text.startswith("{") or not response_text.endswith("}"):
            raise ValueError("Response is not valid JSON format")

        response_json = json.loads(response_text)
        action = response_json.get("action")
        needs_email_content = response_json.get("needs_email_content", False)

        return JSONResponse(content={"action": action, "needs_email_content": needs_email_content})

    except Exception as e:
        print("Gemini error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
