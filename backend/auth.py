from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import os

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for development

router = APIRouter()

# Define the OAuth flow
flow = Flow.from_client_secrets_file(
    "backend/temp/credentials.json",
    scopes=[
        'https://www.googleapis.com/auth/gmail.readonly',        # Read emails
        'https://www.googleapis.com/auth/gmail.send',            # Send emails
        'https://www.googleapis.com/auth/userinfo.email',        # Get user's email address
        'https://www.googleapis.com/auth/userinfo.profile',      # Get user's basic profile (name, picture, etc)
        'openid'                                                 # Required for ID token (OpenID Connect)
    ],
    redirect_uri="http://localhost:8000/login/callback"
)

@router.get("/login")
def login():
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    return RedirectResponse(authorization_url)

@router.get("/login/callback")
def login_callback(request: Request):
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials
    access_token = credentials.token
    return {"access_token": access_token}
