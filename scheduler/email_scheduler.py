import asyncio
import httpx
from datetime import datetime, timedelta, timezone
import pytz  # Make sure pytz is installed
from backend.db.mongo import get_scheduled_emails_collection

BASE_URL = "http://localhost:8000"
IST = pytz.timezone("Asia/Kolkata")

async def send_scheduled_emails():
    collection = get_scheduled_emails_collection()

    while True:
        try:
            # Get current IST time
            now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
            now_ist = now_utc.astimezone(IST)

            print("🔄 Checking for pending emails at IST:", now_ist)

            # Query emails scheduled up to now (in IST)
            pending_emails = await collection.find({
                "status": "pending",
                "scheduled_time": {"$lte": now_ist.isoformat()}
            }).to_list(length=20)

            print(f"📬 Found {len(pending_emails)} scheduled emails")

            for email_doc in pending_emails:
                action = email_doc["action"]
                email_payload = email_doc["email"]

                print("📨 Email payload:", email_payload)

                async with httpx.AsyncClient() as client:
                    if action == "send":
                        response = await client.post(f"{BASE_URL}/send_email", json=email_payload)
                    elif action == "reply":
                        response = await client.post(f"{BASE_URL}/reply", json=email_payload)
                    else:
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

        await asyncio.sleep(60)  # Check every 60 seconds
