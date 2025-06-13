from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
from email.mime.text import MIMEText

router = APIRouter()

@router.post("/send_email")
async def send_email(request: Request):
    # Get token from query param
    user_token = request.query_params.get("user_token")
    if not user_token:
        return JSONResponse(content={"error": "Missing user_token in URL"}, status_code=401)

    try:
        data = await request.json()
        to = data.get("to")
        subject = data.get("subject")
        message_text = data.get("message")

        if not to or not subject or not message_text:
            return JSONResponse(content={"error": "Missing fields"}, status_code=400)

        creds = Credentials(token=user_token)
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(message_text)
        message['to'] = to
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw}

        result = service.users().messages().send(userId='me', body=body).execute()

        return {"message": "Email sent successfully ✅", "id": result.get("id")}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)




