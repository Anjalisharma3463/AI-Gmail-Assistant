from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from bson import ObjectId
from fastapi import HTTPException

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.db.mongo import get_contacts_collection, get_user_collection
 

router = APIRouter()
contacts_collection = get_contacts_collection()
users_collection = get_user_collection()

# 🛠️ Helper to get user_id from access_token
async def get_user_id_from_token(token: str):
    user = await users_collection.find_one({"access_token": token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return str(user["_id"])


# ✅ Save a contact
@router.post("/add-contact")
async def save_contact(request: Request):
    data = await request.json()

    token = request.query_params.get("token")  # or get from headers
    if not token:
        return JSONResponse(content={"error": "Missing token"}, status_code=401)

    user_id = await get_user_id_from_token(token)
    name = data.get("name")
    email = data.get("email")

    if not all([user_id, name, email]):
        return JSONResponse(content={"error": "Missing fields"}, status_code=400)

    new_contact = {
        "user_id": ObjectId(user_id),
        "name": name,
        "email": email
    }

    result = await contacts_collection.insert_one(new_contact)

    return JSONResponse({
        "message": "Contact saved successfully",
        "contact_id": str(result.inserted_id)
    })


# ✅ Get all contacts for a user (based on token)
@router.get("/contacts")
async def get_contacts(request: Request):
    token = request.query_params.get("token")
    if not token:
        return JSONResponse(content={"error": "Missing token"}, status_code=401)

    user_id = await get_user_id_from_token(token)

    contacts_cursor = contacts_collection.find({"user_id": ObjectId(user_id)})
    contacts = []
    async for contact in contacts_cursor:
        contact["_id"] = str(contact["_id"])
        contact["user_id"] = str(contact["user_id"])
        contacts.append(contact)

    return JSONResponse({"contacts": contacts})
