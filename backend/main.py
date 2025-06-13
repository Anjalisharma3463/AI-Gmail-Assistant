from fastapi import FastAPI
from backend import auth, email_reader, summarizer,email_sender
 
 
app = FastAPI()
 
app.include_router(auth.router)
app.include_router(email_reader.router)
app.include_router(summarizer.router)
app.include_router(email_sender.router)



@app.get("/")
def read_root():
    return {"message": "Speakify Backend Running ✅"}
