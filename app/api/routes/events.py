from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.database import get_session
from app.db.models import Club, Event, User, EventRegistration
from app.api.deps import get_current_user
from app.schemas import EventCreate, EventPublic, UserPublic
# Import the recommendation function
from app.ai.recommendations import recommend_events_for_user

router = APIRouter()

# --- New Recommendation Endpoint ---

@router.get("/recommendations", response_model=List[EventPublic])
def get_event_recommendations(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get personalized event recommendations for the current user.
    """
    # We need to fetch the full user object with its relationships loaded
    # A simple db.get(User, current_user.id) would not load relationships by default
    user_with_relations = db.exec(
        select(User).where(User.id == current_user.id)
    ).one()

    all_events = db.exec(select(Event)).all()
    
    recommended_events = recommend_events_for_user(user_with_relations, all_events)
    
    return recommended_events


# --- Existing CRUD for Events ---
# ... (the rest of the file remains the same) ...

@router.post("/", response_model=EventPublic, status_code=status.HTTP_201_CREATED)
def create_event(
    event_in: EventCreate,
    club_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Create a new event for a club. Only the club admin can create events."""
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    
    if club.admin_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the club admin can create events")

    event = Event.model_validate(event_in, update={"club_id": club.id})
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.get("/", response_model=List[EventPublic])
def get_all_events(db: Annotated[Session, Depends(get_session)]):
    """Get a list of all events from all clubs."""
    return db.exec(select(Event)).all()

@router.post("/{event_id}/register", response_model=UserPublic)
def register_for_event(
    event_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Allows the current user to register for an event."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    existing_registration = db.exec(
        select(EventRegistration).where(EventRegistration.user_id == current_user.id, EventRegistration.event_id == event_id)
    ).first()
    if existing_registration:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already registered for this event")

    registration = EventRegistration(user_id=current_user.id, event_id=event_id)
    db.add(registration)
    db.commit()
    
    return current_user