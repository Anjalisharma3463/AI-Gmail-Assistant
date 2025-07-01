from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.utils.read_emails_helper import read_email_helper
from dotenv import load_dotenv
load_dotenv(".env.production")
router = APIRouter()

# ✅ New route that uses the function
@router.post("/search_mails")
async def search_mails(request: Request):
    try:
        print("/search_mails CALLED")
        data = await request.json()
        user_query = data.get("user_query", "")
        user = request.state.user
        user_id = user["user_id"]
        user_email = user["email"]

        result = await read_email_helper(user_id=user_id, user_email=user_email, user_query=user_query)
        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
