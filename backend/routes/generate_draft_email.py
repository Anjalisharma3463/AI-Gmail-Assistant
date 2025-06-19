from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse 
from backend.db.mongo import get_contacts_collection   
import os
import json
import re
from dotenv import load_dotenv

load_dotenv(".env.production")
router = APIRouter()

@router.post("/generate_draft_email")
async def generate_draft_email(request: Request):
    data = await request.json()
    user_prompt = data.get("prompt")

    user = request.state.user
    username = user["username"]
    user_id = user["user_id"]  

    if not user_prompt:
        return JSONResponse(content={"error": "Missing prompt"}, status_code=400)

    try: 
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # 📦 Extract character count like: "in 300 characters" / "within 300 characters"
        match = re.search(r"(?:in|within|of)\s+(\d{2,4})\s*characters", user_prompt.lower())
        char_limit = int(match.group(1)) if match else None

        character_instruction = (
            f"- The email body must be exactly {char_limit} characters long. Be as close as possible without going under. Do not exceed or fall short significantly." 
            if char_limit 
            else "- Write a short, concise professional email body."
        )

        model = genai.GenerativeModel("gemini-2.0-flash")

        # 🔥 Ask Gemini to extract recipient name as well
        response = model.generate_content(f"""
        You are a smart and emotionally aware email writing assistant. The user may give vague instructions and may optionally request a specific email length (like "write in 200 characters").

        Your responsibilities:

        1. **Infer tone** based on context:
        - If user mentions words like **"friend"**, "buddy", "bro", etc → use a **casual** tone
        - If user mentions **"HR"**, "client", "manager", "project", "interview"**, etc → use a **professional** tone

        2. **Extract recipient details**:
        - Try to extract **recipient name** from the user prompt. If not found, use empty string.
        - Use recipient name to personalize salutation.
        - Recipient **email address must be included by the user** in the prompt.

        3. **Respond in this exact JSON format**:
        {{
        "to": "recipient's email address (must be present)",
        "name": "Recipient name (if found, else empty string)",
        "subject": "a short, relevant subject line",
        "message": "email body with salutation, message, and signature"
        }}

        4. **Email structure** must always include:
        - A salutation:
            - If name is available: "Dear [Name]," or "Hey [Name],"
            - If name not available: fallback to "Hello," or "Hi there,"
        - A message body in the **inferred tone**
        - A proper closing:
            - "Sincerely," or "Regards, {username}" for professional
            - "Take care," or "Cheers, {username}" for casual

        5. {character_instruction}

        6. ✨ If user includes contact info (phone number, address, job title, etc.), add it at the end in professional format — but only if present. Do not make anything up.

        7. ⚠️ If **recipient email** is missing, respond ONLY with:
        {{
        "error": "Recipient email address is missing. Please provide a valid email."
        }}

        **Rules:**
        - Output must be final, polished, and ready to send.
        - Do not include any placeholders or incomplete parts.
        - ⚠️ **Respond strictly with plain JSON only** — no markdown, no comments, no explanations, no code blocks.

        User Prompt:
        \"\"\"{user_prompt}\"\"\"
        """)


        gemini_response = response.text.strip()

        if gemini_response.startswith("```"):
            gemini_response = re.sub(r"^```json|^```|```$", "", gemini_response.strip(), flags=re.IGNORECASE).strip()

        email_data = json.loads(gemini_response)

        recipient_name = email_data.get("name", "").strip().lower()
        if not recipient_name:
            return JSONResponse(content={"error": "Recipient email address is missing. Please provide a valid email."}, status_code=400)

        # 🔍 Match with contact collection
        contact_collection = get_contacts_collection()
        contact_doc = await contact_collection.find_one({"name": {"$regex": f"^{recipient_name}$", "$options": "i"}, "user_id": user_id})

        if not contact_doc:
            return JSONResponse(content={"error": "Recipient email address is missing. Please provide a valid email."}, status_code=400)

        email_data["to"] = contact_doc["email"]

        return JSONResponse(content={
            "status": "draft_generated",
            "character_limit": char_limit,
            "email": email_data
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
