import uvicorn
import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.utils.dependencies import get_current_user
from backend.routes import (
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

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background scheduler startup hook
@app.on_event("startup")
async def start_scheduler():
    print("🚀 Scheduler task started on app startup")
    asyncio.create_task(send_scheduled_emails())

# Health check route
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

# Dev entry point
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
