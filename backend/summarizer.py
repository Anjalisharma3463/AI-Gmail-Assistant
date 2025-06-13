from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter()

@router.post("/summarize")
async def summarize(request: Request):
    try:
        data = await request.json()
        email_text = data.get("email_text")

        if not email_text:
            return JSONResponse(content={"error": "No email text provided"}, status_code=400)

        prompt = f"Summarize this email in simple terms and in short:\n\n{email_text}"

        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            contents=[prompt],
            generation_config=genai.GenerationConfig(
                max_output_tokens=70,
                temperature=0.7
            )
        )

        summary = response.text.strip()
        print("Gemini response:", summary)
        return {"summary": summary}

    except Exception as e:
        print("Gemini error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
