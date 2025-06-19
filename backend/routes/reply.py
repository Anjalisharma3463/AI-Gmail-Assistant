from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from backend.utils.google_auth import get_valid_credentials
import base64
import os
import re
from email.mime.text import MIMEText
import google.auth

# as input
    # "email": {
    #     "to": "anjalisharma1562005@gmail.com",
    #     "subject": "Re: Meeting tomorrow",
    #     "message": "Hey Anjali,\n\nGot it, see you at 10 AM tomorrow!\n\nCheers, Swati Sharma",
    #     "message_id": "1976a04a085bb02d",
    #     "thread_id": "1976a04a085bb02d"
    # }

router = APIRouter()

@router.post("/reply")
async def reply_to_email(request: Request):
    data = await request.json()
    user = request.state.user
    user_email = user["email"]
    to_email = data.get("to")
    subject = data.get("subject")
    message_body = data.get("message")
    thread_id = data.get("thread_id")
    msg_id = data.get("message_id")  # original message id for reply header

    if not (to_email and subject and message_body and thread_id):
        return JSONResponse(content={"error": "Missing required fields"}, status_code=400)

    try:
        creds = await get_valid_credentials(user_email)
        service = build("gmail", "v1", credentials=creds)

        # Create raw MIME message
        message = MIMEText(message_body)
        message['to'] = to_email
        message['from'] = user_email
        message['subject'] = f"Re: {subject}"
        if msg_id:
            message['In-Reply-To'] = msg_id
            message['References'] = msg_id

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        send_result = service.users().messages().send(
            userId='me',
            body={
                'raw': raw_message,
                'threadId': thread_id
            }
        ).execute()
        print(f"Reply sent successfully: {send_result['id']}")
        return {"status": "reply_sent", "message_id": send_result['id']}

    except Exception as e:
        print("Error sending reply:", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)
