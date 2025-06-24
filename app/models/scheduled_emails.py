from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime

class ScheduledEmailCreate(BaseModel):
    user_id: str
    action: Literal["send", "reply"]
    email: dict  # should contain to, subject, message, (optionally thread_id, message_id)
    scheduled_time: datetime
    status: Literal["pending", "sent"] = "pending"
