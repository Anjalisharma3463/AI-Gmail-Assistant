from pydantic import BaseModel, EmailStr
from typing import Optional

class ContactCreate(BaseModel):
    name: str
    email: EmailStr

class ContactResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    user_id: str
