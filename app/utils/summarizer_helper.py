import re
from fastapi import APIRouter, Request
import google.generativeai as genai

def normalize_email(email):
    """Remove dots and get only name part of email."""
    return email.lower().replace(".", "").split("@")[0]

async def summarize_single_email(email, logged_in_email, username):
    body = email.get("body", "")
    subject = email.get("subject", "")
    to = email.get("to", "")
    from_email = email.get("from", "")

    if not all([body, subject, to, from_email]):
        raise Exception("Missing fields in individual email")

    # Check direction
    is_user_sender = normalize_email(from_email) == normalize_email(logged_in_email)
    other_party_email = to if is_user_sender else from_email

    name_match = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b", subject + " " + body)
    extracted_name = name_match.group(1) if name_match else other_party_email.split("@")[0].replace(".", " ").replace("_", " ").title()

    action_line = (
        f"You (logged in as {username}) sent an email to {extracted_name} ({other_party_email})."
        if is_user_sender else
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
        "summary": summary,
        "from": from_email,
        "to": to,
        "direction": "sent" if is_user_sender else "received",
        "name_detected": extracted_name
    }
