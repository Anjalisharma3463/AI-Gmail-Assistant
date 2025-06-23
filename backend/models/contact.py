from pydantic import BaseModel
from typing import Optional

class ContactCreate(BaseModel):
    name: str
    email: str

class ContactResponse(BaseModel):
    id: str
    name: str
    email: str
    user_id: str
