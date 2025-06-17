from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from jose import jwt
from datetime import datetime, timedelta
from bson import ObjectId
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.db.mongo import get_user_collection

router = APIRouter()
user_collection = get_user_collection()

# Allow HTTP for local testing
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# JWT secret for session generation (store in .env in real app)
JWT_SECRET = "your_jwt_secret_here"
JWT_EXPIRATION_MINUTES = 60 * 24 * 7  # 7 days session

# OAuth config
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

@router.get("/login")
async def login():
    # Check if user has logged in before and has a refresh token
    # This part needs front/backend integration or cookie/session check
    # For now always prompt consent to ensure first-time refresh_token retrieval
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='select_account',  # ensure refresh_token on first login
        include_granted_scopes='true'
    )
    return RedirectResponse(auth_url)

@router.get("/login/callback")
async def login_callback(request: Request):
    try:
        # Step 1: Exchange code for tokens
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials

        # Step 2: Extract user info from id_token
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, requests.Request()
        )

        user_email = id_info.get("email")
        username = id_info.get("name")
        picture = id_info.get("picture")

        # Step 3: Save user or login
        existing_user = await user_collection.find_one({"email": user_email})
        user_data = {
            "email": user_email,
            "username": username,
            "picture": picture,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,  # May be None if not first time
            "token_expiry": credentials.expiry.isoformat(),
            "has_refresh_token": bool(credentials.refresh_token)
        }

        if existing_user:
            update_data = {
                "$set": {
                    "access_token": credentials.token,
                    "token_expiry": credentials.expiry.isoformat(),
                }
            }
            if credentials.refresh_token:
                update_data["$set"]["refresh_token"] = credentials.refresh_token
                update_data["$set"]["has_refresh_token"] = True
            await user_collection.update_one({"_id": existing_user["_id"]}, update_data)
            user_id = str(existing_user["_id"])
        else:
            result = await user_collection.insert_one(user_data)
            user_id = str(result.inserted_id)

        # Step 4: Create JWT session token
        session_payload = {
            "user_id": user_id,
            "email": user_email,
            "username": username,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        }
        session_token = jwt.encode(session_payload, JWT_SECRET, algorithm="HS256")

        return JSONResponse({
            "message": "Login successful",
            "user_id": user_id,
            "session_token": session_token,
            "email": user_email,
            "username": username,
            "picture": picture,
            "access_token":credentials.token
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
