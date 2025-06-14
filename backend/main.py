from fastapi import FastAPI
from backend.api import email_reader, summarizer,email_sender,voice_api, query_generator
from backend.api import auth
  

app = FastAPI()
 
app.include_router(auth.router)
app.include_router(email_reader.router)
app.include_router(summarizer.router)
app.include_router(email_sender.router)
app.include_router(voice_api.router)
app.include_router(query_generator.router)



@app.get("/")
def read_root():
    return {"message": "Speakify Backend Running ✅"}
