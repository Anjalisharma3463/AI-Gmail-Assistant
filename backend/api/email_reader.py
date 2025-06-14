from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter()


@router.get("/read_emails")
async def read_emails(
    token: str = Query(default=None),
    user_query: str = Query(default="Find mails that talk about joining instructions or orientation from college")
):
    if not token:
        return JSONResponse(content={"error": "User not authenticated"}, status_code=401)

    try:
        # Step 1: Generate Gmail query using Gemini
        prompt = f"""
        You are an assistant that helps convert user language into Gmail search queries.

        Rules:
        - Use Gmail search operators only.
        - Try to capture multiple keyword variations.
        - If user is vague, infer helpful words from typical email subjects.
        - Use OR for multiple possibilities.
        - Focus on words in subject lines or sender names.

        Today's date is {datetime.utcnow().strftime('%Y/%m/%d')}.

        Now convert this user input into a Gmail search query:
        "{user_query}"

        Respond with Gmail search query only.
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
        print("Gmail Query from Gemini:", gmail_query)

        # Step 2: Gmail API call using the generated query
        creds = Credentials(token=token)
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
