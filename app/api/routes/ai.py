import os
from datetime import datetime
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

# --- Local Imports ---
from app.db.database import get_session
from app.db.models import Club, Event
from app.core.config import GEMINI_API_KEY # Assuming you have this in your config

# --- Google Gemini ---
import google.generativeai as genai

router = APIRouter()

# --- Configure the Gemini client ---
# This is the correct way to configure the API key.
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    # This warning will show in your backend console on startup if the key is missing.
    print("Warning: GEMINI_API_KEY is not set. Chatbot functionality will be disabled.")

# --- Pydantic Models for Request/Response ---
class ChatQuery(BaseModel):
    query: str
    history: List[dict] = []

class ChatResponse(BaseModel):
    response: str

# --- Database Context Function ---
def get_university_context(db: Session) -> str:
    """Fetches all club and event data from the DB to provide context to the AI."""
    clubs = db.exec(select(Club)).all()
    events = db.exec(select(Event).where(Event.date >= datetime.now())).all()

    context = "Here is the current information about the university's clubs and events:\n\n"
    
    context += "=== Clubs ===\n"
    if clubs:
        for club in clubs:
            context += f"- {club.name}: {club.description}\n"
    else:
        context += "No clubs are currently listed.\n"
        
    context += "\n=== Upcoming Events ===\n"
    if events:
        for event in events:
            event_date = event.date.strftime("%B %d, %Y")
            context += f"- {event.name} on {event_date} at {event.location}. Description: {event.description}\n"
    else:
        context += "No upcoming events are currently scheduled.\n"
        
    return context

# --- API Endpoint ---
@router.post("/chatbot", response_model=ChatResponse, tags=["AI"])
async def handle_chat_query(
    query: ChatQuery,
    db: Annotated[Session, Depends(get_session)],
):
    # If the key was never set during startup, disable the endpoint.
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured on the server."
        )

    # 1. Get current data from the database
    university_context = get_university_context(db)

    # 2. Format the chat history for the prompt
    formatted_history = ""
    for message in query.history:
        role = "User" if message.get('from') == 'user' else "StellarHub Assistant"
        formatted_history += f"{role}: {message.get('text')}\n"

    # 3. Construct the final prompt for Gemini
    prompt = f"""
    You are StellarHub Assistant, a friendly and helpful AI guide for students at Sitare University.

    **Core Instructions:**
    1.  **Prioritize Context:** Base all specific answers about clubs and events directly on the information in the "CONTEXT FROM DATABASE" section. Do not invent details.
    2.  **Handle Missing Information:** If the answer is not in the context, you MUST respond with: "I don't have that specific information right now, but you can likely find it on the official university website."
    3.  **Be a Recommender:** Use the context to provide helpful suggestions for general questions (e.g., "What tech clubs are there?").
    4.  **Maintain Persona:** Always be friendly, positive, and keep answers concise.

    --- CONTEXT FROM DATABASE ---
    {university_context}
    --- END OF CONTEXT ---

    --- CONVERSATION HISTORY ---
    {formatted_history}
    --- END OF HISTORY ---

    Based on all of the above, answer the user's question.
    User Question: "{query.query}"
    """

    try:
        # 4. Call the Gemini API
        model = genai.GenerativeModel('gemini-pro')
        response = await model.generate_content_async(prompt)
        
        return {"response": response.text}

    except Exception as e:
        print(f"Gemini API Error: {e}") # Log the specific error to your backend console
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while communicating with the AI service."
        )