from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse 
import os
import json
import re

router = APIRouter()

@router.post("/generate_draft_email")
async def generate_draft_email(request: Request):
    data = await request.json()
    user_prompt = data.get("prompt")

    user = request.state.user
    username = user["username"]
    if not user_prompt:
        return JSONResponse(content={"error": "Missing prompt"}, status_code=400)

    try: 
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # 📦 Extract character count like: "in 300 characters" / "within 300 characters"
        match = re.search(r"(?:in|within|of)\s+(\d{2,4})\s*characters", user_prompt.lower())
        char_limit = int(match.group(1)) if match else None

        # ✍️ Gemini instruction for strict character count
        character_instruction = (
            f"- The email body must be exactly {char_limit} characters long. Be as close as possible without going under. Do not exceed or fall short significantly." 
            if char_limit 
            else "- Write a short, concise professional email body."
        )

        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(f"""
        You are a smart and emotionally aware email writing assistant. The user may give vague instructions and may optionally request a specific email length (like "write in 200 characters").

        Your responsibilities:

        1. First, **infer the tone** based on relationship:
        - If user mentions words like **"friend"**, "buddy", "bro", etc → use a **casual** tone
        - If user mentions **"HR"**, "client", "manager", "project", "interview", etc → use a **professional** tone

        2. Extract strictly and return this exact JSON:
        {{
        "to": "recipient's email address (must be present)",
        "subject": "a short, relevant subject line",
        "message": "email body with proper structure"
        }}

        3. The email body must always contain:
        - A salutation:
            - Use "Dear [Name]," or "Hey [Name]," if the recipient's name is mentioned or can be inferred.
            - If the name is unclear, use a neutral salutation like "Hello," or "Hi there,".
        - A message body in the **inferred tone**
        - A proper closing (like:
            - "Sincerely," or "Regards, {username}" for professional
            - "Take care," or "Cheers, {username}" for casual)

        4. {character_instruction}

        5. ✨ If the user includes any personal contact details in the prompt (like phone number, address, designation, etc.), add those at the end of the email body in a professional format — but only if provided. Do not fabricate them.

        ⚠️ If recipient email is missing, respond ONLY with:
        {{
        "error": "Recipient email address is missing. Please provide a valid email."
        }}

        Rules:
        - The email must sound ready to send.
        - Do not leave any placeholders, brackets, or incomplete parts.
        - Respond in plain JSON only. No markdown, no comments.

        ⚠️ Your output MUST be **plain JSON only**, no markdown, no code blocks, and no extra text.

        User instruction:
        \"\"\"{user_prompt}\"\"\"
        """)

        gemini_response = response.text.strip()

        # 🧼 Clean response if backticks or ```json
        if gemini_response.startswith("```"):
            gemini_response = re.sub(r"^```json|^```|```$", "", gemini_response.strip(), flags=re.IGNORECASE).strip()

        email_data = json.loads(gemini_response)

        # 🔁 If Gemini returns error message
        if "error" in email_data:
            return JSONResponse(content=email_data, status_code=400)

        return JSONResponse(content={
            "status": "draft_generated",
            "character_limit": char_limit,
            "email": email_data
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
