from fastapi import APIRouter
from backend.voice.listen import listen_and_transcribe

router = APIRouter()

@router.get("/voice/listen")
def listen_voice():
    try:
        result = listen_and_transcribe()
        return {"transcript": result}
    except Exception as e:
        return {"error": str(e)}
