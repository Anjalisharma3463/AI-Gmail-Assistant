from fastapi import APIRouter
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
 
router = APIRouter()
#Not storing session so for now passing token here just for testing purposes right now.

#pass token like /read_emails?token=your_token_here
@router.get("/read_emails")
def read_emails(token: str = None):
    if not token:
        return JSONResponse(content={"error": "User not authenticated"}, status_code=401)

    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials(token=token)
        service = build('gmail', 'v1', credentials=creds)

        result = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = result.get('messages', [])

        email_summaries = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            snippet = msg_data.get('snippet')
            email_summaries.append({
                "id": msg['id'],
                "snippet": snippet
            })

        return {"emails": email_summaries}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
