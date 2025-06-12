from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
import os

# Optional: connect to Mongo if you want to persist token
# from backend.mongo import users_collection

router = APIRouter()

# Allow HTTP for development only
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Global temporary store (you can replace with database)
user_credentials: Credentials = None
user_email: str = None

# OAuth Flow setup
flow = Flow.from_client_secrets_file(
    "backend/temp/credentials.json",
    scopes=[
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid'
    ],
    redirect_uri="http://localhost:8000/login/callback"
)

# Step 1: Redirect user to Google OAuth page
@router.get("/login")
def login():
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # to get refresh token
        include_granted_scopes='true'
    )
    return RedirectResponse(authorization_url)


# Step 2: Handle Google's callback
@router.get("/login/callback")
def login_callback(request: Request):
    global user_credentials, user_email

    try:
        # Exchange authorization code for access token
        flow.fetch_token(authorization_response=str(request.url))
        user_credentials = flow.credentials

        # Get user info from ID token
        id_info = id_token.verify_oauth2_token(
            user_credentials.id_token,
            requests.Request()
        )
        user_email = id_info.get("email")

        # ✅ Optional: store in MongoDB
        # users_collection.update_one(
        #     {"email": user_email},
        #     {"$set": {"access_token": user_credentials.token}},
        #     upsert=True
        # )

        print("✅ User credentials obtained successfully.")
        print("🔐 Access Token:", user_credentials.token)
        print("📧 Email:", user_email)

        return JSONResponse({
            "message": "Login successful",
            "email": user_email,
            "access_token": user_credentials.token
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
