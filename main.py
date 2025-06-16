import uvicorn
from fastapi import FastAPI

from backend.routes import auth, email_reader, summarizer, email_sender, voice_api , generate_draft_email

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Speakify backend running ✅"}

# Register all routers
app.include_router("/api/v1",auth.router)
app.include_router("/api/v1",email_reader.router)
app.include_router("/api/v1",summarizer.router)
app.include_router("/api/v1",email_sender.router)
app.include_router("/api/v1",voice_api.router)
app.include_router("/api/v1",generate_draft_email.router)
# Main entry point
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
