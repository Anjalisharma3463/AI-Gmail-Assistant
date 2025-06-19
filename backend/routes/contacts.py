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
 

# ✅ Save a contact
@router.post("/add-contact")
async def save_contact(request: Request):
    
    user = request.state.user
    username = user["username"]
    user_id = user["user_id"]
    logged_in_email = user["email"]
   
    name = request.get("name")
    email = request.get("email")

    print("Logged-in username:", username)
    print("Logged-in email:", logged_in_email)
    if not all([user_id, username, logged_in_email]):
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
    
    user = request.state.user
    username = user["username"]
    user_id = user["user_id"]
    logged_in_email = user["email"]
    print("Logged-in username:", username)
    print("Logged-in email:", logged_in_email)

    contacts_cursor = contacts_collection.find({"user_id": ObjectId(user_id)})
    contacts = []
    async for contact in contacts_cursor:
        contact["_id"] = str(contact["_id"])
        contact["user_id"] = str(contact["user_id"])
        contacts.append(contact)

    return JSONResponse({"contacts": contacts})
