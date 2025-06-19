from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.db.mongo import get_contacts_collection
import os
import json
import re
from dotenv import load_dotenv
from bson import ObjectId

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
        print("❌ Missing prompt in request.")
        return JSONResponse(content={"error": "Missing prompt"}, status_code=400)

    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # 📦 Extract optional character limit
        match = re.search(r"(?:in|within|of)\s+(\d{2,4})\s*characters", user_prompt.lower())
        char_limit = int(match.group(1)) if match else None

        character_instruction = (
            f"- The email body must be exactly {char_limit} characters long. Be as close as possible without going under. Do not exceed or fall short significantly."
            if char_limit
            else "- Write a short, concise professional email body."
        )

        model = genai.GenerativeModel("gemini-2.0-flash")

        print(f"\n🔍 Prompt sent to Gemini:\n{user_prompt}\n")

        response = model.generate_content(f"""
        You are a smart and emotionally aware email writing assistant. The user may give vague instructions and may optionally request a specific email length (like "write in 200 characters").

        Your responsibilities:

        1. **Infer tone** based on context:
        - If user mentions words like "friend", "buddy", "bro", etc → use a **casual** tone
        - If user mentions "HR", "client", "manager", "project", "interview", etc → use a **professional** tone

        2. **Extract recipient details**:
        - Try to extract **recipient name** from the user prompt.
        - Leave "to" (email) blank if the user didn't provide it.

        3. **Respond in this exact JSON format**:
        {{
        "to": "",  
        "name": "Recipient name if available, else empty string",
        "subject": "a short, relevant subject line",
        "message": "email body with salutation, message, and closing"
        }}

        4. Email format rules:
        - Start with a salutation:
            - "Dear [Name]," or "Hey [Name],"
            - If no name: fallback to "Hello," or "Hi there,"
        - Use inferred tone in message
        - End with a closing like:
            - "Sincerely," or "Regards, {username}" for professional
            - "Take care," or "Cheers, {username}" for casual

        5. {character_instruction}

        6. If contact info (phone, role) is in prompt, add at the end professionally — but never fabricate.

        ⚠️ Do NOT use placeholders like "someone@example.com".
        ⚠️ Output must be **pure JSON only**. No markdown, code blocks, or comments.

        User Prompt:
        \"\"\"{user_prompt}\"\"\"
        """)

        gemini_response = response.text.strip()
        print("\n📨 Raw Gemini response:\n", gemini_response)

        if gemini_response.startswith("```"):
            gemini_response = re.sub(r"^```json|^```|```$", "", gemini_response.strip(), flags=re.IGNORECASE).strip()

        email_data = json.loads(gemini_response)

        recipient_name = email_data.get("name", "").strip()
        recipient_email = email_data.get("to", "").strip()

        print(f"\n👤 Extracted Name: {recipient_name}")
        print(f"📧 Extracted Email: {recipient_email if recipient_email else 'None'}")

        if not recipient_email:
            # 🔍 Try to resolve from contacts DB using flexible regex
            contact_collection = get_contacts_collection()
            print(f"📡 Searching in DB: name ~ '{recipient_name}', user_id = {user_id}")

            contacts_cursor = contact_collection.find({
                "name": {"$regex": f".*{re.escape(recipient_name)}.*", "$options": "i"},
                "user_id": ObjectId(user_id)
            })
            matching_contacts = await contacts_cursor.to_list(length=5)
            print("🔍 Matching Contacts:", matching_contacts)

            if matching_contacts:
                print("✅ Contact match found.")
                email_data["to"] = matching_contacts[0]["email"]
            else:
                print("❌ No matching contact found. Fetching all contacts for user.")
                all_contacts = await contact_collection.find({"user_id": user_id}).to_list(length=10)
                print("📄 All contacts for user:", all_contacts)

                return JSONResponse(
                    content={"error": "Recipient email address is missing. Please provide a valid email."},
                    status_code=400
                )

        print("✅ Final Draft Email Data:", email_data)

        return JSONResponse(content={
            "status": "draft_generated",
            "character_limit": char_limit,
            "email": email_data
        })

    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)
