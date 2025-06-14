from fastapi import APIRouter
from backend.utils.listen import listen_and_transcribe
from fastapi import Request
from backend.utils.speak import speak_text
 
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
