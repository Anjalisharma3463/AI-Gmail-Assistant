from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.db.mongo import get_contacts_collection
import os
import json
import re
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime
import dateparser
load_dotenv(".env.production")
router = APIRouter()

# using this route for sending new mail using /send_email
# using this route for sending reply to a mail using /reply
# using this route for saving a scheduled mail in database and will later use /send_email and /reply.
 
@router.post("/generate_draft_email")
async def generate_draft_email(request: Request):
    data = await request.json()
    user_prompt = data.get("prompt")
    original_email = data.get("original_email")  # Optional original email content for replies
    action = data.get("action", "new")  # "reply" or "new"

    user = request.state.user
    username = user["username"]
    user_id = user["user_id"]
    print("original_email: ", original_email)
    print("action: ", action)

    if not user_prompt:
        print("❌ Missing prompt in request.")
        return JSONResponse(content={"error": "Missing prompt"}, status_code=400)

    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
 
        match = re.search(r"(?:in|within|of)\s+(\d{2,4})\s*characters", user_prompt.lower())
        char_limit = int(match.group(1)) if match else None

        character_instruction = (
            f"- The email body must be exactly {char_limit} characters long. Be as close as possible without going under. Do not exceed or fall short significantly."
            if char_limit
            else "- Write a short, concise professional email body."
        )

        model = genai.GenerativeModel("gemini-2.0-flash")

        print(f"\n🔍 Prompt sent to Gemini:\n{user_prompt}\n")

        original_email_instruction = (
            f"\n\n6. If this is a reply, below is the original email you're replying to. Use it to personalize your tone and context:\n\n---\n{original_email['body']}\n---\n"
            if action == "reply" and original_email else ""
        )

        full_prompt = f"""
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
        {original_email_instruction}

        ⚠️ Do NOT use placeholders like "someone@example.com".
        ⚠️ Output must be **pure JSON only**. No markdown, code blocks, or comments.

        User Prompt:
        {user_prompt} 
        """

        response = model.generate_content(full_prompt)


        gemini_response = response.text.strip()
        print("\n📨 Raw Gemini response:\n", gemini_response)

        if gemini_response.startswith("```"):
            gemini_response = re.sub(r"^```json|^```|```$", "", gemini_response.strip(), flags=re.IGNORECASE).strip()

        email_data = json.loads(gemini_response)

        recipient_name = email_data.get("name", "").strip()
        recipient_email = email_data.get("to", "").strip()
        print(f"\n👤 Extracted Name: {recipient_name}")
        print(f"📧 Extracted Email: {recipient_email if recipient_email else 'None'}")

        # 🔍 Extract schedule time from prompt
        # Step 1: Ask Gemini to extract time expression
        time_extraction_prompt = f"""
        Extract only the datetime expression from this message. Don't explain anything.
        User message: "{user_prompt}"
        Respond with only the time phrase (like "tomorrow at 9am", "June 19th 6PM", etc), or "none" if no time is mentioned.
        """

        time_response = model.generate_content(time_extraction_prompt)
        time_string = time_response.text.strip().replace("`", "").strip('"').strip()

        print("🕒 Gemini Extracted Time String:", time_string)

        # Step 2: Use dateparser to parse it into datetime
        scheduled_time = dateparser.parse(time_string)

        if scheduled_time:
            now = datetime.utcnow()
            if scheduled_time <= now:
                return JSONResponse(content={"error": "Scheduled time must be in the future."}, status_code=400)
            scheduled_time = scheduled_time.isoformat()
            print("⏰ Final Parsed Scheduled Time:", scheduled_time)
        else:
            print("⚠️ Gemini didn't extract any valid time.")


        if scheduled_time:
            from backend.db.mongo import get_scheduled_emails_collection
            scheduled_collection = get_scheduled_emails_collection()

            scheduled_email_doc = {
                "user_id": ObjectId(user_id),
                "action": action,
                "email": {
                    "to": email_data["to"],
                    "subject": email_data["subject"],
                    "message": email_data["message"],
                    "name": email_data.get("name", ""),
                    "emailid": email_data.get("emailid"),        # only if it's a reply
                    "threadid": email_data.get("threadid")       # only if it's a reply
                },
                "scheduled_time": scheduled_time,
                "status": "pending"
            }

            await scheduled_collection.insert_one(scheduled_email_doc)
            print("📥 Scheduled email saved in correct format.")



        if action == "reply":
            original_email_id = original_email['emailid']
            original_thread_id = original_email['threadid']
            email_data["emailid"] = original_email_id
            email_data["threadid"] = original_thread_id
            print("📧 Original Email ID:", original_email_id)
            print("📧 Original Thread ID:", original_thread_id)

        if not recipient_email:
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
                all_contacts = await contact_collection.find({"user_id": ObjectId(user_id)}).to_list(length=10)
                print("📄 All contacts for user:", all_contacts)

                return JSONResponse(
                    content={"error": "Recipient email address is missing. Please provide a valid email."},
                    status_code=400
                )

        print("✅ Final Draft Email Data:", email_data)

        return JSONResponse(content={
            "status": "draft_generated",
            "character_limit": char_limit,
            "email": email_data,
            "original_email_id": original_email_id if action == "reply" else None,
            "original_thread_id": original_thread_id if action == "reply" else None,
            "action": action,
            "recipient_name": recipient_name,
            "recipient_email": recipient_email
        })

    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)
