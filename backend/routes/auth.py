from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from bson import ObjectId
import os

# ✅ Import MongoDB collection
from db.mongo import get_user_collection

router = APIRouter()
user_collection = get_user_collection()

# Allow HTTP for development only
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Global temporary store (can replace with database session)
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
async def login_callback(request: Request):
    global user_credentials, user_email

    try:
        # 🌐 Exchange authorization code for access token
        flow.fetch_token(authorization_response=str(request.url))
        user_credentials = flow.credentials

        # 🔍 Get user info from ID token
        id_info = id_token.verify_oauth2_token(
            user_credentials.id_token,
            requests.Request()
        )
        user_email = id_info.get("email")
        username = id_info.get("name")
        pictureurl = id_info.get("picture")

        # ✅ Check if user already exists
        existing_user = await user_collection.find_one({"email": user_email})

        if existing_user:
            user_id = str(existing_user["_id"])
        else:
            # ➕ Create new user
            new_user = {
                "email": user_email,
                "username": username,
                "picture": pictureurl,
                "access_token": user_credentials.token
            }
            result = await user_collection.insert_one(new_user)
            user_id = str(result.inserted_id)

        # ✅ Return user info and user_id
        return JSONResponse({
            "message": "Login successful",
            "user_id": user_id,
            "user_email": user_email,
            "access_token": user_credentials.token,
            "username": username,
            "picture": pictureurl
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
