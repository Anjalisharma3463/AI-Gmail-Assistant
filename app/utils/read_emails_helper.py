# app/routes/search_emails.py


from app.utils.google_auth import get_valid_credentials
from app.db.mongo import get_contacts_collection
from bson import ObjectId

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import base64
import re
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(".env.production")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))



# ✅ Reusable helper function
async def read_email_helper(user_id, user_email, user_query: str):
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    prompt = f"""
    You are an intelligent assistant that converts **natural language email requests** into **Gmail search queries** using Gmail’s advanced search operators.

    📅 Today's date is: {today.strftime('%Y/%m/%d')}

    🎯 Your task:
    Understand what the user wants to find in their Gmail account and return a valid Gmail search query string. No explanation — just the query.

    🔧 Rules to follow:
    1. ✅ Use Gmail operators like: `from:`, `to:`, `subject:`, `has:`, `after:`, `before:`, `filename:`, `is:important`, `category:`, etc.
    2. ✅ If user says “I sent”, “sent by me”, use → `from:me`
    3. ✅ If user says “they sent me”, “I received”, “I got”, use → `to:me`
    4. ✅ If user says “sent to [person/email]” → use: `to:[person] from:me`
    5. ✅ If user says “received from [person/email]” → use: `from:[person] to:me`
    6. Ignore reply word and summary word in user query.
    7. ❓ If sender/recipient is unclear → default to `to:me`
    8. 🔁 For keyword-based searches use:
    - subject:keyword OR body:keyword
    9. 🕐 For time-based queries like "today", use:
    - `after:{today.strftime('%Y/%m/%d')} before:{tomorrow.strftime('%Y/%m/%d')}`
    10. 💬 Use `is:unread` if query says unread or missed from OR if query says last or latest then use `newer_than:1d`.
    11. ❌ Never include explanation — output only the final **Gmail query string**
    12. 📎 For file/attachment related queries:
    - Use `has:attachment`
    - If user says “resume”, “assignment”, “report”, “slides”, etc:
    → add `filename:assignment` or relevant word.
    - Match partial names inside filenames, not exact only.


    ---

    🔁 Now convert this user input into a Gmail search query:
    "{user_query}"
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        contents=[prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=60,
        )
    )
    gmail_query = response.text.strip()

    if not gmail_query:
        gmail_query = f'to:me subject:({user_query}) OR body:({user_query}) after:{today.strftime("%Y/%m/%d")} before:{tomorrow.strftime("%Y/%m/%d")}'

    # Fix (me), (inbox) to just me, inbox
    special_tokens = ['me', 'inbox', 'starred']
    for token in special_tokens:
        gmail_query = re.sub(rf'\({token}\)', token, gmail_query, flags=re.IGNORECASE)

    # 📥 Substitute contact names with email
    matched = False
    if not re.search(r'(from|to):\S+@\S+', gmail_query):
        contact_collection = get_contacts_collection()
        all_contacts = await contact_collection.find({"user_id": ObjectId(user_id)}).to_list(length=100)
        for contact in all_contacts:
            contact_name = contact["name"].lower().strip()
            contact_email = contact["email"]
            gmail_query = gmail_query.replace('"', '')  # remove quotes for match
            if contact_name in gmail_query.lower() or any(part in gmail_query.lower() for part in contact_name.split()):
                matched = True
                for part in contact_name.split():
                    gmail_query = re.sub(rf'(?<=from:)\s*{re.escape(part)}\b', contact_email, gmail_query, flags=re.IGNORECASE)
                    gmail_query = re.sub(rf'(?<=to:)\s*{re.escape(part)}\b', contact_email, gmail_query, flags=re.IGNORECASE)

        if not matched:
            raise Exception("Name not found in contacts. Please provide the email address of the person.")

    gmail_query = re.sub(r'from:me to:([^\s]+) OR from:\1 to:me', r'(from:me to:\1) OR (from:\1 to:me)', gmail_query)

    creds = await get_valid_credentials(user_id)
    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().list(userId='me', q=gmail_query).execute()

    messages = result.get('messages', [])
    email_summaries = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_data.get("payload", {})
        headers = payload.get("headers", [])
        emailid = msg['id']
        threadid = msg['threadId']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        receiver = next((h['value'] for h in headers if h['name'] == 'To'), '')
        snippet = msg_data.get("snippet", "")

        body = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part["body"].get("data", "")
                    body = base64.urlsafe_b64decode(data + '==').decode("utf-8", errors="ignore")
                    break
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data + '==').decode("utf-8", errors="ignore")

        email_summaries.append({
            "id": emailid,
            "from": sender,
            "to": receiver,
            "subject": subject,
            "date": date,
            "snippet": snippet,
            "body": body,
            "emailid": emailid,
            "threadid": threadid
        })

    return {"emails": email_summaries, "gmail_query": gmail_query}

