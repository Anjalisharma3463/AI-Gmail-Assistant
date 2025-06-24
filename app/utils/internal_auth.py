# app/utils/internal_auth.py

from fastapi import Header, HTTPException, Depends , Request, status
import os
from dotenv import load_dotenv

load_dotenv(".env.production")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

def verify_internal_api_key(request: Request):
    api_key = request.headers.get("x-api-key")
    print("verification started of internal api key...")
    if api_key != INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized internal API call"
        )
 