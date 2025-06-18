from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import jwt
from datetime import datetime, timedelta
from bson import ObjectId
import os
import sys
from dotenv import load_dotenv
load_dotenv()



sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.db.mongo import get_user_collection

router = APIRouter()
user_collection = get_user_collection()

# Allow HTTP for local testing
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# JWT secret for session generation (store securely in .env)
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "10080"))


# OAuth config

flow = Flow.from_client_config(
    {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
            "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_CERT_URL"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")]
        }
    },
    scopes=[
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid'
    ],
    redirect_uri=os.getenv("GOOGLE_REDIRECT_URI")
)
@router.get("/login")
async def login():
    # First-time login: Google will provide refresh_token if not previously granted
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return RedirectResponse(auth_url)

@router.get("/login/callback")
async def login_callback(request: Request):
    try:
        # Step 1: Exchange code for token
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials

        # Step 2: Verify and extract user info
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, requests.Request()
        )

        user_email = id_info.get("email")
        username = id_info.get("name")
        picture = id_info.get("picture")

        # Step 3: Check if user exists in DB
        existing_user = await user_collection.find_one({"email": user_email})

        user_data = {
            "email": user_email,
            "username": username,
            "picture": picture,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,  # May be None
            "token_expiry": credentials.expiry.isoformat(),
            "has_refresh_token": bool(credentials.refresh_token)
        }

        if existing_user:
            update_data = {
                "$set": {
                    "access_token": credentials.token,
                    "token_expiry": credentials.expiry.isoformat()
                }
            }

            # Only store refresh_token if it's new and we didn't have one before
            if credentials.refresh_token and not existing_user.get("refresh_token"):
                update_data["$set"]["refresh_token"] = credentials.refresh_token
                update_data["$set"]["has_refresh_token"] = True

            await user_collection.update_one({"_id": existing_user["_id"]}, update_data)
            user_id = str(existing_user["_id"])
        else:
            result = await user_collection.insert_one(user_data)
            user_id = str(result.inserted_id)

        # Step 4: Create session JWT
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
            "picture": picture
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
