from pydantic import BaseModel, EmailStr
from typing import Optional

# For inserting a user
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    picture: Optional[str] = None
    access_token: str

# For reading a user (e.g., in response)
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    picture: Optional[str] = None
