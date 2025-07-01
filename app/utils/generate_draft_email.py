 
from app.db.mongo import get_contacts_collection
import os
import json
import re
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime
import dateparser

load_dotenv(".env.production")
 
async def generate_draft_email(
    user: dict,
    user_query: str,
    action: str = "new",
    original_email: dict = None
):
    print("📨 generate_draft_email CALLED")

    username = user["username"]
    user_id = user["user_id"]

    if not user_query:
        raise ValueError("Missing prompt")

    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    match = re.search(r"(?:in|within|of)\s+(\d{2,4})\s*characters", user_query.lower())
    char_limit = int(match.group(1)) if match else None

    character_instruction = (
        f"- The email body must be exactly {char_limit} characters long. Be as close as possible without going under. Do not exceed or fall short significantly."
        if char_limit
        else "- Write a short, concise professional email body."
    )

    model = genai.GenerativeModel("gemini-2.0-flash")

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
        {user_query} 
        """

    response = model.generate_content(full_prompt)
    gemini_response = response.text.strip()

    if gemini_response.startswith("```"):
        gemini_response = re.sub(r"^```json|^```|```$", "", gemini_response.strip(), flags=re.IGNORECASE).strip()

    email_data = json.loads(gemini_response)

    recipient_name = email_data.get("name", "").strip()
    recipient_email = email_data.get("to", "").strip()

    # Time extraction
    time_response = model.generate_content(f"Extract only the datetime expression...\nUser message: \"{user_query}\"")
    time_string = time_response.text.strip().replace("`", "").strip('"').strip()
    scheduled_time = dateparser.parse(time_string)

    if scheduled_time and scheduled_time <= datetime.utcnow():
        raise ValueError("Scheduled time must be in the future")

    if scheduled_time:
        from app.db.mongo import get_scheduled_emails_collection
        scheduled_collection = get_scheduled_emails_collection()

        scheduled_email_doc = {
            "user_id": ObjectId(user_id),
            "action": action,
            "email": {
                "to": email_data["to"],
                "subject": email_data["subject"],
                "message": email_data["message"],
                "name": email_data.get("name", ""),
                "emailid": original_email.get("emailid") if original_email else None,
                "threadid": original_email.get("threadid") if original_email else None,
            },
            "scheduled_time": scheduled_time.isoformat(),
            "status": "pending"
        }
        await scheduled_collection.insert_one(scheduled_email_doc)

    if action == "reply" and original_email:
        email_data["emailid"] = original_email['emailid']
        email_data["threadid"] = original_email['threadid']

    if not recipient_email:
        contact_collection = get_contacts_collection()
        contacts_cursor = contact_collection.find({
            "name": {"$regex": f".*{re.escape(recipient_name)}.*", "$options": "i"},
            "user_id": ObjectId(user_id)
        })
        matching_contacts = await contacts_cursor.to_list(length=5)
        if matching_contacts:
            print("✅ Contact match found.")
            email_data["to"] = matching_contacts[0]["email"]
        else:
            raise ValueError("Recipient email address is missing.")

    return {
        "status": "draft_generated",
        "character_limit": char_limit,
        "email": email_data,
        "original_email_id": email_data.get("emailid"),
        "original_thread_id": email_data.get("threadid"),
        "action": action,
        "recipient_name": recipient_name,
        "recipient_email": email_data["to"]
    }
