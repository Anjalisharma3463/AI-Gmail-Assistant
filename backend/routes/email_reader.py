from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime, timedelta
from backend.utils.google_auth import get_valid_credentials
from backend.db.mongo import get_contacts_collection
import re
from bson import ObjectId

load_dotenv(".env.production")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter()

@router.post("/read_emails")
async def read_emails(request: Request):
    try:
        data = await request.json()
        user_query = data.get("user_query", "Find mails that talk about joining instructions or orientation from college")
        user = request.state.user
        user_email = user["email"]
        user_id = user["user_id"]

        creds = await get_valid_credentials(user_email)
        print('creds', creds)

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
        6. ❓ If sender/recipient is unclear → default to `to:me`
        7. 🔁 For keyword-based searches use:
        - subject:keyword OR body:keyword
        8. 🕐 For time-based queries like "today", use:
        - `after:{today.strftime('%Y/%m/%d')} before:{tomorrow.strftime('%Y/%m/%d')}`
        9. 💬 Use `is:unread` if query says unread
        10. ❌ Never include explanation — output only the final **Gmail query string**

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

        # fix parentheses around 'me', 'inbox', etc.
        special_tokens = ['me', 'inbox', 'starred']
        for token in special_tokens:
            gmail_query = re.sub(rf'\({token}\)', token, gmail_query, flags=re.IGNORECASE)

        print("Gmail Query from Gemini:", gmail_query)

        # 📥 Substitute contact names with their emails
        contact_collection = get_contacts_collection()
        all_contacts = await contact_collection.find({"user_id": ObjectId(user_id)}).to_list(length=100)

        print("contacts found from database : ", all_contacts)

        # Replace contact names with emails in Gmail query
        for contact in all_contacts:
            contact_name = contact["name"].lower()
            contact_email = contact["email"]

            # Full name
            gmail_query = re.sub(rf'from:\(?{re.escape(contact_name)}\)?', f'from:{contact_email}', gmail_query, flags=re.IGNORECASE)
            gmail_query = re.sub(rf'to:\(?{re.escape(contact_name)}\)?', f'to:{contact_email}', gmail_query, flags=re.IGNORECASE)

            # Each part of name
            for part in contact_name.split():
                gmail_query = re.sub(rf'from:\(?{re.escape(part)}\)?', f'from:{contact_email}', gmail_query, flags=re.IGNORECASE)
                gmail_query = re.sub(rf'to:\(?{re.escape(part)}\)?', f'to:{contact_email}', gmail_query, flags=re.IGNORECASE)

        # ✅ Wrap OR queries in parentheses
        gmail_query = re.sub(r'from:me to:([^\s]+) OR from:\1 to:me', r'(from:me to:\1) OR (from:\1 to:me)', gmail_query)

        print("Final Gmail Query after contact substitution:", gmail_query)


        service = build('gmail', 'v1', credentials=creds)
        result = service.users().messages().list(userId='me', q=gmail_query).execute()

        messages = result.get('messages', [])
        count_mails = 0
        email_summaries = []

        for msg in messages:
            count_mails += 1
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = msg_data.get("payload", {})
            headers = payload.get("headers", [])

            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
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
                "id": msg['id'],
                "sender": sender,
                "subject": subject,
                "date": date,
                "snippet": snippet,
                "body": body
            })

        print(f"Total emails fetched: {count_mails}")
        return {"emails": email_summaries, "gmail_query": gmail_query}

    except Exception as e:
        print("Error in /read_emails:", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)
