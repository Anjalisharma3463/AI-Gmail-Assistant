import uvicorn
from fastapi import FastAPI, Depends 
from fastapi.middleware.cors import CORSMiddleware 
from backend.utils.dependencies import get_current_user

from backend.routes import auth, email_reader, summarizer, email_sender, voice_api , generate_draft_email, contacts, reply

app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Speakify backend running ✅"}

# Register all routers with the same prefix
app.include_router(auth.router)  # keep this public
app.include_router(email_reader.router, dependencies=[Depends(get_current_user)])
app.include_router(summarizer.router, dependencies=[Depends(get_current_user)])
app.include_router(email_sender.router, dependencies=[Depends(get_current_user)])
app.include_router(voice_api.router, dependencies=[Depends(get_current_user)])
app.include_router(generate_draft_email.router, dependencies=[Depends(get_current_user)])
app.include_router(contacts.router, dependencies=[Depends(get_current_user)])
app.include_router(reply.router, dependencies=[Depends(get_current_user)])
# Main entry point
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
