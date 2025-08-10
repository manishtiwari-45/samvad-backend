from typing import List, Annotated
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_session
from app.db.models import EventPhoto, User, Event
from app.api.deps import get_current_user

router = APIRouter()

# --- Schemas ---
# Yeh schema batata hai ki photo ke saath event ki thodi info bhi bhejenge
class EventInfo(BaseModel):
    id: int
    name: str

class PhotoWithDetails(BaseModel):
    id: int
    image_url: str
    timestamp: datetime
    event: EventInfo

# --- Endpoint ---
@router.get("/", response_model=List[PhotoWithDetails])
def get_all_photos(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get all photos from all events, sorted by most recent.
    """
    # Sabhi photos ko database se get karein, naye timestamp ke hisaab se sort karke
    photos = db.exec(select(EventPhoto).order_by(EventPhoto.timestamp.desc())).all()
    
    return photos