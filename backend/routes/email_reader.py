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
load_dotenv()
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
         
        # ✅ Get valid Google credentials (auto-refreshes if expired)
        creds = await get_valid_credentials(user_email)
        print('creds',creds)
        # Step 1: Generate Gmail query using Gemini
        prompt = f"""
        You are an intelligent assistant that converts **natural language email requests** into **Gmail search queries** using Gmail’s advanced search operators.

        📅 Today's date is: {datetime.utcnow().strftime('%Y/%m/%d')}

        🎯 Your task:
        Understand what the user wants to find in their Gmail account and return a valid Gmail search query string. No explanation — just the query.

        🔧 Rules to follow:
        1. ✅ Use Gmail operators like: `from:`, `to:`, `subject:`, `has:`, `after:`, `before:`, `filename:`, `is:important`, `category:`, etc.
        2. ✅ If user says “I sent”, “sent by me”, use → `from:me`
        3. ✅ If user says “they sent me”, “I received”, “I got”, use → `to:me`
        4. ✅ If user says “sent to [person/email]” → use: `to:[person] from:me`
        5. ✅ If user says “received from [person/email]” → use: `from:[person] to:me`
        6. ❓ If sender/recipient is unclear → default to `to:me`
        7. 🔁 For keyword-based searches (like “instagram”, “meeting”, “OTP”) use:
        - **Multiple keyword combinations using `OR`**
        - Search both subject and body (e.g. `subject:instagram OR body:instagram`)
        8. 🕐 For time-based queries (e.g. “last week”, “yesterday”) infer `after:` and `before:` based on today’s date
        9. 💬 Use wildcards, partial matches, and known email categories like:
        - `category:promotions`, `category:social`, `filename:pdf`, `is:important`, etc.
        10. ❌ Never include explanation — output only the final **Gmail query string**

        ---

        📌 Common Email Types and How to Handle:

        - **Instagram / social media** → subject:instagram OR subject:"follow request" OR body:instagram
        - **Meeting invites / links** → subject:invite OR subject:meeting OR body:meet.google.com OR body:zoom.us
        - **College info** → subject:college OR subject:admission OR body:orientation
        - **Job / resume** → subject:resume OR subject:job OR filename:resume.pdf
        - **OTP / verification** → subject:OTP OR subject:code OR body:verification
        - **Newsletters** → category:promotions OR subject:newsletter
        - **Bills / payments** → subject:payment OR subject:invoice OR subject:bill
        - **Important alerts** → is:important OR subject:alert

        ---

        🧪 Examples:

        Input: "show me emails about instagram follow requests"
        Output: to:me subject:instagram OR subject:"follow request" OR body:instagram OR body:insta

        Input: "emails I sent to my friend Anjali"
        Output: to:anjali from:me

        Input: "emails I got from college about orientation"
        Output: from:* to:me subject:college OR subject:joining OR subject:orientation OR body:college

        Input: "resume emails from recruiters"
        Output: to:me subject:resume OR subject:job OR from:recruiter OR filename:resume.pdf

        Input: "OTP I received yesterday"
        Output: to:me subject:OTP OR subject:code OR body:verification after:{(datetime.utcnow() - timedelta(days=1)).strftime('%Y/%m/%d')}

        Input: "promotional newsletters I got this week"
        Output: to:me category:promotions after:{(datetime.utcnow() - timedelta(days=7)).strftime('%Y/%m/%d')}

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
            gmail_query = f'subject:({user_query}) OR body:({user_query})'

        print("Gmail Query from Gemini:", gmail_query)

        # Step 2: Gmail API call using the generated query

        service = build('gmail', 'v1', credentials=creds)
        result = service.users().messages().list(userId='me', q=gmail_query).execute()

        messages = result.get('messages', [])
        count_mails = 0
        email_summaries = []

        # Step 3: Parse and format each email
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