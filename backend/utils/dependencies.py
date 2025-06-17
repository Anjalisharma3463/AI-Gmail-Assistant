# backend/utils/dependencies.py

from fastapi import Request, HTTPException, Depends
from jose import jwt, JWTError
from datetime import datetime
import os

# Store this in .env or use dotenv
JWT_SECRET = "your_jwt_secret_here"

async def get_current_user(request: Request):
    # Get token from Authorization header (Bearer <token>)
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        exp = payload.get("exp")
        username = payload.get("username")
        email = payload.get("email")
        user_id = payload.get("user_id")
        print(f"Decoded JWT payload: {payload}")
        if exp is None or datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=401, detail="Token expired")

        # You can return user_id or full payload here
        user = {
            "user_id": user_id,
            "email": email,
            "username": username,
            "user_id": user_id
        }
        request.state.user = user
        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
