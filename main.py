import uvicorn
from fastapi import FastAPI

from backend.routes import auth, email_reader, summarizer, email_sender, voice_api , generate_draft_email

app = FastAPI()

@app.get("/api/v1")
def root():
    return {"message": "Speakify backend running ✅"}

# Register all routers with the same prefix
app.include_router(auth.router, prefix="/api/v1")
app.include_router(email_reader.router, prefix="/api/v1")
app.include_router(summarizer.router, prefix="/api/v1")
app.include_router(email_sender.router, prefix="/api/v1")
app.include_router(voice_api.router, prefix="/api/v1")
app.include_router(generate_draft_email.router, prefix="/api/v1")

# Main entry point
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
