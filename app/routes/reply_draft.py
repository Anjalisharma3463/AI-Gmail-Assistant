from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
load_dotenv(".env.production")
router = APIRouter()
from app.utils.generate_draft_email import generate_draft_email

@router.post("/reply_draft")
async def reply_draft_route(request: Request):
    data = await request.json()
    user = request.state.user
    try:
        response = await generate_draft_email(user, data.get("user_query"), action="reply", original_email=data.get("original_email"))
        return JSONResponse(content=response)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
