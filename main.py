import uvicorn
import asyncio
from fastapi import FastAPI, Depends, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
 
from app.utils.dependencies import get_current_user
from app.routes import (
    auth,
    email_reader,
    summarizer,
    email_sender,
    voice_api,
    generate_draft_email,
    contacts,
    reply, 
)

from scheduler.email_scheduler import send_scheduled_emails 
import os
from dotenv import load_dotenv
from app.routes import internal
from app.utils.internal_auth import verify_internal_api_key
load_dotenv(".env.production")
 
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

# ✅ Internal API key dependency
def verify_internal_api_key(x_api_key: str = Header(...)):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized access to internal route")
    return True

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background scheduler startup hook
@app.on_event("startup")
async def start_scheduler():
    print("🚀 Scheduler task started on app startup")
    asyncio.create_task(send_scheduled_emails())
 
@app.get("/")
def root():
    return {"message": "✅ Speakify backend running"}




# Public router
app.include_router(auth.router)

# Protected routers (require JWT)
protected_routers = [
    email_reader.router,
    summarizer.router,
    email_sender.router,
    voice_api.router,
    generate_draft_email.router,
    contacts.router,
    reply.router, 
]
for router in protected_routers:
    app.include_router(router, dependencies=[Depends(get_current_user)])

app.include_router(internal.router,  dependencies=[Depends(verify_internal_api_key)])

# Dev entry point
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
