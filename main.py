import uvicorn
from fastapi import FastAPI

from backend.api import auth, email_reader, summarizer, email_sender, voice_api

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Speakify backend running ✅"}

# Register all routers
app.include_router(auth.router)
app.include_router(email_reader.router)
app.include_router(summarizer.router)
app.include_router(email_sender.router)
app.include_router(voice_api.router) 

# Main entry point
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
