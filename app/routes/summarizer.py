from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import os, re
from dotenv import load_dotenv
import google.generativeai as genai
from app.utils.summarizer_helper import summarize_single_email
load_dotenv(".env.production")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter()



@router.post("/summarize")
async def summarize(request: Request):
    try:
        print("📨 /summarize CALLED")
        user = request.state.user
        username = user["username"]
        logged_in_email = user["email"]

        data = await request.json()

        # 🧠 CASE 1: Multiple emails
        if "emails" in data and isinstance(data["emails"], list):
            results = []
            for email in data["emails"]:
                result = await summarize_single_email(email, logged_in_email, username)
                results.append(result)
            return {"summaries": results}

        # 🧠 CASE 2: Single email
        elif all(k in data for k in ("body", "subject", "to", "from")):
            result = await summarize_single_email(data, logged_in_email, username)
            return {"summary": result}

        else:
            return JSONResponse(content={"error": "Invalid input structure."}, status_code=400)

    except Exception as e:
        print("Gemini error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
