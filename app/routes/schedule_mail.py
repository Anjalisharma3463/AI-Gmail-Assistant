from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from datetime import datetime
import dateparser

from app.db.mongo import get_scheduled_emails_collection
from app.utils import get_current_user  # Assuming you use JWT or similar auth

router = APIRouter()

class ScheduleEmailInput(BaseModel):
    email: dict  # should contain to, subject, message, name, optional emailid, threadid
    action: str  # "new" or "reply"
    scheduled_time: str  # natural text like "tomorrow 9 AM" or ISO string

@router.post("/schedule_mail")
async def schedule_mail(data: ScheduleEmailInput, user: dict = Depends(get_current_user)):
    try:
        # Parse the user-provided time using dateparser
        parsed_time = dateparser.parse(data.scheduled_time)

        if not parsed_time:
            raise HTTPException(status_code=400, detail="Could not parse the scheduled time.")

        if parsed_time <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="Scheduled time must be in the future.")

        scheduled_collection = get_scheduled_emails_collection()

        # Save the email in DB
        await scheduled_collection.insert_one({
            "user_id": ObjectId(user["user_id"]),
            "action": data.action,
            "email": {
                "to": data.email["to"],
                "subject": data.email["subject"],
                "message": data.email["message"],
                "name": data.email.get("name", ""),
                "emailid": data.email.get("emailid"),
                "threadid": data.email.get("threadid"),
            },
            "scheduled_time": parsed_time.isoformat(),
            "status": "pending"
        })

        return {"status": "scheduled", "scheduled_for": parsed_time.isoformat()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
