# app/routes/internal.py

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
import os

from app.utils.google_auth import get_valid_credentials

router = APIRouter()

# ------------------ /internal/send_email ------------------

@router.post("/internal/send_email")
async def internal_send_email(request: Request):
    try:
        print("📨 /internal/send_email CALLED")
        data = await request.json()
        user_email = data.get("user_email")
        username = data.get("username", "System")
        user_id = data.get("user_id")
        to = data.get("to")
        subject = data.get("subject")
        message_text = data.get("message")

        if not (user_id and to and subject and message_text):
            return JSONResponse(content={"error": "Missing required fields"}, status_code=400)

        creds = await get_valid_credentials(user_id)
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(message_text)
        message['to'] = to
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw}

        result = service.users().messages().send(userId='me', body=body).execute()

        return {
            "message": "Internal email sent ✅",
            "email_id": result.get("id"),
            "sent_by": username,
            "from_email": user_email,
        }

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ------------------ /internal/reply ------------------

@router.post("/internal/reply")
async def internal_reply_email(request: Request):
    try:
        print("📨 /internal/reply CALLED")
        data = await request.json()
        user_email = data.get("user_email")
        user_id = data.get("user_id")
        to_email = data.get("to")
        subject = data.get("subject")
        message_body = data.get("message")
        thread_id = data.get("threadid")
        msg_id = data.get("emailid")

        if not all([user_id, to_email, subject, message_body, thread_id]):
            return JSONResponse(content={"error": "Missing required fields"}, status_code=400)

        creds = await get_valid_credentials(user_id)
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(message_body)
        message['to'] = to_email
        message['from'] = user_email
        message['subject'] = f"Re: {subject}"

        if msg_id:
            message['In-Reply-To'] = msg_id
            message['References'] = msg_id

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = service.users().messages().send(
            userId='me',
            body={'raw': raw_message, 'threadId': thread_id}
        ).execute()

        return {"status": "Internal reply sent ✅", "message_id": result['id']}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
