from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText

# Import your token refresh utility
from backend.utils.google_auth import get_valid_credentials

router = APIRouter()

@router.post("/send_email")
async def send_email(request: Request):
    try:
        user = request.state.user
        user_email = user["email"]
        username = user["username"]
        user_id = user["user_id"]
        # ✅ Get valid Google credentials (auto-refreshes if expired)
        creds = await get_valid_credentials(user_id) 
        data = await request.json() 
        to = data.get("to")
        subject = data.get("subject")
        message_text = data.get("message")

        if not to or not subject or not message_text:
            return JSONResponse(content={"error": "Missing fields"}, status_code=400)

        # ✅ Build Gmail API client using valid credentials
        service = build('gmail', 'v1', credentials=creds)

        # Build and encode message
        message = MIMEText(message_text)
        message['to'] = to
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw}

        # Send email via Gmail API
        result = service.users().messages().send(userId='me', body=body).execute()

        return {
            "message": "Email sent successfully ✅",
            "email_id": result.get("id"),
            "sent_by": username,
            "from_email": user_email,
        }

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
