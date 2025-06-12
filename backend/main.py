from fastapi import FastAPI
from backend import auth

app = FastAPI()

# Include OAuth routes
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Speakify Backend Running ✅"}
