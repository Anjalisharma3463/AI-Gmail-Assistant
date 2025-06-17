from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import os, re
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter()

def normalize_email(email):
    """Remove dots and get only name part of email."""
    return email.lower().replace(".", "").split("@")[0]

@router.post("/summarize")
async def summarize(request: Request):
    try:
        user = request.state.user
        username = user["username"]
        logged_in_email = user["email"]
        print("Logged-in username:", username)
        print("Logged-in email:", logged_in_email)

        data = await request.json()
        body = data.get("body", "")
        subject = data.get("subject", "")
        to = data.get("to", "")
        from_email = data.get("from", "")

        if not all([body, subject, to, from_email]):
            return JSONResponse(content={"error": "Missing fields"}, status_code=400)

        # Step 1: Check if the logged-in user is sender
        is_user_sender = normalize_email(from_email) == normalize_email(logged_in_email)
        other_party_email = to if is_user_sender else from_email

        # Step 2: Extract name from subject/body/email
        name_match = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b", subject + " " + body)
        extracted_name = name_match.group(1) if name_match else other_party_email.split("@")[0].replace(".", " ").replace("_", " ").title()

        # Step 3: Create personalized prompt
        if is_user_sender:
            action_line = (
                f"You (logged in as {username}) sent an email to {extracted_name} ({other_party_email})."
            )
        else:
            action_line = (
                f"{extracted_name} ({other_party_email}) sent an email to you (logged in as {username})."
            )

        prompt = (
            f"{action_line}\n\n"
            f"Summarize this email in short and in one or two sentences and simple terms.\n"
            f"Make sure to say 'you' if the logged-in user sent or received it and don't mention logged-in user name and Avoid repeating details unnecessarily.\n"
            f"Be friendly, short, and clear.\n\n"
            f"Subject: {subject}\n"
            f"Body: {body}"
        )

        # Step 4: Gemini call
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            contents=[prompt],
            generation_config=genai.GenerationConfig(
                max_output_tokens=80,
                temperature=0.7
            )
        )

        summary = response.text.strip()

        return {
            "email": {
                "summary": summary,
                "from": from_email,
                "to": to,
                "direction": "sent" if is_user_sender else "received",
                "name_detected": extracted_name,
                "logged_in_user": logged_in_email
            }
        }

    except Exception as e:
        print("Gemini error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
