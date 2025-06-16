from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGO_URI)
db = client["AI_Gmail_Assistant_DB"]

users_collection = db["users"]
contacts_collection = db["contacts"]
