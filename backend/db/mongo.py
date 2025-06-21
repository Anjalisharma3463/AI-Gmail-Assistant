from motor.motor_asyncio import AsyncIOMotorClient
import os
 
from dotenv import load_dotenv

load_dotenv(".env.production")
MONGO_URL = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URL)
db = client["AI-Gmail-Assistant-Database"]

def get_user_collection():
    return db["users"]

def get_contacts_collection():
    return db["contacts"]
