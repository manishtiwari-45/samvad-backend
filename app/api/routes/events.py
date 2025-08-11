from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlmodel import Session, select
from pydantic import BaseModel
import cloudinary
import cloudinary.uploader

from app.core.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
from app.db.database import get_session
# Import UserRole to check for super_admin
from app.db.models import Club, Event, User, EventRegistration, EventPhoto, UserRole
from app.api.deps import get_current_user
from app.schemas import EventCreate, EventPublic, UserPublic
from app.ai.recommendations import recommend_events_for_user

# Cloudinary Configuration
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)

router = APIRouter()

class EventPhotoPublic(BaseModel):
    id: int
    image_url: str

# --- Photo Gallery Endpoints ---
@router.post("/{event_id}/photos", response_model=EventPhotoPublic, status_code=status.HTTP_201_CREATED)
def upload_photo_for_event(
    event_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.club.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to upload photos for this event")
        
    try:
        upload_result = cloudinary.uploader.upload(file.file, folder="campusconnect_events")
        image_url = upload_result.get("secure_url")
        public_id = upload_result.get("public_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {e}")

    new_photo = EventPhoto(image_url=image_url, public_id=public_id, event_id=event_id)
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)
    
    return new_photo

@router.get("/{event_id}/photos", response_model=List[EventPhotoPublic])
def get_photos_for_event(event_id: int, db: Annotated[Session, Depends(get_session)]):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.photos

@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_photo(
    photo_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    photo_to_delete = db.get(EventPhoto, photo_id)
    if not photo_to_delete:
        raise HTTPException(status_code=404, detail="Photo not found")

    event = db.get(Event, photo_to_delete.event_id)
    if not event or event.club.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this photo")

    try:
        cloudinary.uploader.destroy(photo_to_delete.public_id)
    except Exception as e:
        print(f"Could not delete photo {photo_to_delete.public_id} from Cloudinary: {e}")

    db.delete(photo_to_delete)
    db.commit()
    
    return None

# --- Existing Event Endpoints ---
@router.get("/recommendations", response_model=List[EventPublic])
def get_event_recommendations(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    user_with_relations = db.exec(select(User).where(User.id == current_user.id)).one()
    all_events = db.exec(select(Event)).all()
    recommended_events = recommend_events_for_user(user_with_relations, all_events)
    return recommended_events

@router.post("/", response_model=EventPublic, status_code=status.HTTP_201_CREATED)
def create_event(
    event_in: EventCreate, club_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")

    # --- MODIFIED AUTHORIZATION CHECK ---
    # A user can create an event if they are the admin of that club OR if they are a super admin.
    is_club_admin = (club.admin_id == current_user.id)
    is_super_admin = (current_user.role == UserRole.super_admin)

    if not (is_club_admin or is_super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create events for this club."
        )
    # --- END OF MODIFICATION ---

    event = Event.model_validate(event_in, update={"club_id": club.id})
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.get("/", response_model=List[EventPublic])
def get_all_events(db: Annotated[Session, Depends(get_session)]):
    return db.exec(select(Event)).all()

@router.post("/{event_id}/register", response_model=UserPublic)
def register_for_event(
    event_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    existing_registration = db.exec(select(EventRegistration).where(EventRegistration.user_id == current_user.id, EventRegistration.event_id == event_id)).first()
    if existing_registration:
        raise HTTPException(status_code=400, detail="User is already registered for this event")
        
    registration = EventRegistration(user_id=current_user.id, event_id=event_id)
    db.add(registration)
    db.commit()
    return current_user