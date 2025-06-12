from fastapi import FastAPI
from backend import auth , email_reader

app = FastAPI()

# Include OAuth routes
app.include_router(auth.router)
app.include_router(email_reader.router)

@app.get("/")
def read_root():
    return {"message": "Speakify Backend Running ✅"}
