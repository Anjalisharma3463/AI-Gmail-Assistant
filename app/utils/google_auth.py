from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from google.auth.exceptions import RefreshError
from datetime import datetime
from app.db.mongo import get_user_collection
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv(".env.production")

user_collection = get_user_collection()

async def get_valid_credentials(user_id: str):
    # ✅ Convert user_id to ObjectId
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise Exception("Invalid user ID format")

    # 🔍 Fetch user from DB
    db_user = await user_collection.find_one({"_id": object_id})
    if not db_user:
        raise Exception("User not found")

    access_token = db_user.get("access_token")
    refresh_token = db_user.get("refresh_token")
    token_expiry = db_user.get("token_expiry")

    if not refresh_token:
        raise Exception("No refresh token available. Please login again.")

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )

    # Refresh only if token is expired
    if datetime.utcnow() > datetime.fromisoformat(token_expiry):
        try:
            print("🔁 Access token expired. Refreshing...")
            creds.refresh(GoogleRequest())

            await user_collection.update_one(
                {"_id": object_id},
                {"$set": {
                    "access_token": creds.token,
                    "token_expiry": creds.expiry.isoformat()
                }}
            )

        except RefreshError:
            raise Exception("Refresh token is invalid or revoked. Please log in again.")

    return creds
