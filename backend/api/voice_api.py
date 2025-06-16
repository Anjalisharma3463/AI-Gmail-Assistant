
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.utils.listen import listen_and_transcribe
from backend.utils.speak import speak_text
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/voice/listen")
def listen_voice():
    try:
        result = listen_and_transcribe()
        return {"transcript": result}
    except Exception as e:
        return {"error": str(e)}

 
@router.post("/voice/speak")
async def speak_response(request: Request):
    try:
        data = await request.json()
        text = data.get("text")

        if not text:
            return {"error": "No text to speak"}

        result = speak_text(text)
        return {"message": result}
    except Exception as e:
        return {"error": str(e)}
