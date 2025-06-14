from fastapi import APIRouter
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
from datetime import datetime 


router = APIRouter()

@router.get("/read_emails")
def read_emails(token: str = None):
    if not token:
        return JSONResponse(content={"error": "User not authenticated"}, status_code=401)

    try:
        creds = Credentials(token=token)
        service = build('gmail', 'v1', credentials=creds)

        result = service.users().messages().list(userId='me').execute()
        messages = result.get('messages', [])

        email_summaries = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = msg_data.get("payload", {})
            headers = payload.get("headers", [])

            # Extract useful headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            snippet = msg_data.get("snippet", "")

            # Decode email body (simplified for text/plain part)
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

            # Store complete data
            email_summaries.append({
                "id": msg['id'],
                "sender": sender,
                "subject": subject,
                "date": date,
                "snippet": snippet,
                "body": body
            })

        return {"emails": email_summaries}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
