import asyncio
import httpx
from datetime import datetime, timezone
import pytz
from backend.db.mongo import get_scheduled_emails_collection
import os
from dotenv import load_dotenv

load_dotenv(".env.production")

BASE_URL = os.getenv("BASE_URL")
IST = pytz.timezone("Asia/Kolkata")
headers = {"x-api-key": os.getenv("INTERNAL_API_KEY")}

async def send_scheduled_emails():
    collection = get_scheduled_emails_collection()

    while True:
        try:
            now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
            now_ist = now_utc.astimezone(IST)
 

            pending_emails = await collection.find({
                "status": "pending",
                "scheduled_time": {"$lte": now_ist.isoformat()}
            }).to_list(length=20)
 

            async with httpx.AsyncClient() as client:
                for email_doc in pending_emails:
                    action = email_doc["action"]
                    email_payload = email_doc["email"]
                    
                    #  Add user_id to payload so internal API can use it
                    email_payload["user_id"] = str(email_doc["user_id"])
 

                    if action == "send":
                        response = await client.post(f"{BASE_URL}/internal/send_email", json=email_payload, headers=headers)
                    elif action == "reply":
                        response = await client.post(f"{BASE_URL}/internal/reply", json=email_payload, headers=headers)
                    else:
                        print(f"⚠️ Unknown action: {action}")
                        continue

                    if response.status_code == 200:
                        await collection.update_one(
                            {"_id": email_doc["_id"]},
                            {"$set": {"status": "sent"}}
                        )
                        print(f"✅ Email sent: {email_doc['_id']}")
                    else:
                        print(f"❌ Failed to send email {email_doc['_id']}: {response.text}")

        except Exception as e:
            print("❌ Scheduler error:", str(e))

        await asyncio.sleep(60)
