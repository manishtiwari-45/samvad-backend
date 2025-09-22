from typing import List, Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlmodel import Session, select
from twilio.rest import Client
import cloudinary
import cloudinary.uploader

from app.core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
from app.core.secure_error_handler import SecureErrorHandler, SecureValidator
from app.db.database import get_session
from app.db.models import User, Club, UserRole, Announcement, Membership
from app.api.deps import get_current_user, get_admin_or_super_admin, get_super_admin
from app.schemas import ClubCreate, ClubPublic, ClubWithMembersAndEvents, UserPublic, AnnouncementCreate, AnnouncementPublic

router = APIRouter()

# Initialize Twilio Client
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None

# --- CRUD for Clubs ---
@router.post("/", response_model=ClubPublic, status_code=status.HTTP_201_CREATED)
def create_club(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_admin_or_super_admin)],
    # Required form fields
    name: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...),
    # New optional form fields
    category: str = Form("General"),
    contact_email: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    founded_date: Optional[str] = Form(None, description="Date in YYYY-MM-DD format"),
    coordinator_id: Optional[int] = Form(None),
    sub_coordinator_id: Optional[int] = Form(None)
):
    """
    Create a new club with a cover photo and additional details.
    Only Admins and SuperAdmins can create clubs.
    """

    # Step 1: Upload cover photo to Cloudinary securely
    try:
        # Use secure upload function
        from app.core.cloudinary_utils import upload_to_cloudinary
        upload_result = upload_to_cloudinary(file, "samvad_clubs")
        image_url = upload_result.get("secure_url")
    except HTTPException:
        # Re-raise validation/upload errors
        raise
    except Exception as e:
        # Handle unexpected errors securely
        raise SecureErrorHandler.handle_file_upload_error(e, "club cover image upload")

    # Step 2: Prepare all club data
    founded_datetime = datetime.fromisoformat(founded_date) if founded_date else None
    
    new_club_data = {
        "name": name,
        "description": description,
        "cover_image_url": image_url,
        "admin_id": current_user.id,
        "category": category,
        "contact_email": contact_email,
        "website_url": website_url,
        "founded_date": founded_datetime,
        "coordinator_id": coordinator_id,
        "sub_coordinator_id": sub_coordinator_id
    }
    
    # Filter out None values so model defaults are used
    club_data_to_validate = {k: v for k, v in new_club_data.items() if v is not None}
    club = Club.model_validate(club_data_to_validate)
    
    db.add(club)
    db.commit()
    db.refresh(club)
    
    # Also make the admin a member of the club
    membership = Membership(user_id=current_user.id, club_id=club.id)
    db.add(membership)
    db.commit()
    
    db.refresh(club)
    return club

# ... (THE REST OF YOUR FUNCTIONS LIKE GET, UPDATE, DELETE, ETC. REMAIN THE SAME) ...
@router.get("/", response_model=List[ClubPublic])
def get_all_clubs(db: Annotated[Session, Depends(get_session)]):
    return db.exec(select(Club)).all()

@router.get("/{club_id}", response_model=ClubWithMembersAndEvents)
def get_club_by_id(club_id: int, db: Annotated[Session, Depends(get_session)]):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club

@router.put("/{club_id}", response_model=ClubPublic)
def update_existing_club(
    club_id: int, 
    club_update: ClubCreate,
    db: Annotated[Session, Depends(get_session)], 
    current_user: Annotated[User, Depends(get_current_user)]
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    if club.admin_id != current_user.id and current_user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this club")
    
    club_data = club_update.model_dump(exclude_unset=True)
    for key, value in club_data.items():
        setattr(club, key, value)
    
    db.add(club)
    db.commit()
    db.refresh(club)
    return club

@router.delete("/{club_id}", response_model=dict)
def delete_existing_club(
    club_id: int, 
    db: Annotated[Session, Depends(get_session)], 
    current_user: Annotated[User, Depends(get_current_user)]
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    if club.admin_id != current_user.id and current_user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this club")
    
    db.delete(club)
    db.commit()
    return {"message": "Club deleted successfully"}

@router.post("/{club_id}/join", response_model=UserPublic)
def join_club(
    club_id: int, db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    existing_membership = db.exec(select(Membership).where(Membership.user_id == current_user.id, Membership.club_id == club_id)).first()
    if existing_membership:
        raise HTTPException(status_code=400, detail="User is already a member of this club")
    membership = Membership(user_id=current_user.id, club_id=club_id)
    db.add(membership)
    db.commit()
    return current_user

@router.post("/{club_id}/announcements", response_model=AnnouncementPublic, status_code=status.HTTP_201_CREATED)
def create_announcement_for_club(
    club_id: int, announcement_in: AnnouncementCreate, db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    # Allow club admin, coordinator, sub-coordinator, or super admin to post announcements
    is_authorized = (
        club.admin_id == current_user.id or
        club.coordinator_id == current_user.id or
        club.sub_coordinator_id == current_user.id or
        current_user.role == UserRole.super_admin
    )
    
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Only club admin, coordinators, or super admin can post announcements")
    
    announcement = Announcement.model_validate(announcement_in, update={"club_id": club_id})
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    
    if twilio_client:
        try:
            users_to_notify = db.exec(select(User).where(User.whatsapp_verified == True, User.whatsapp_consent == True)).all()
            message_body = (f"📢 New Announcement from *{club.name}*!\n\n"
                            f"*{announcement.title}*\n\n{announcement.content}")
            for user in users_to_notify:
                if user.whatsapp_number:
                    try:
                        twilio_client.messages.create(
                            from_=TWILIO_WHATSAPP_NUMBER, body=message_body,
                            to=f"whatsapp:{user.whatsapp_number}"
                        )
                    except Exception as e:
                        # Secure logging - don't expose phone numbers
                        sanitized_phone = SecureValidator.sanitize_phone_number(user.whatsapp_number)
                        SecureErrorHandler.log_error(e, f"WhatsApp send to {sanitized_phone}")
        except Exception as e:
            SecureErrorHandler.log_error(e, "WhatsApp notification process")

    return announcement

@router.get("/{club_id}/announcements", response_model=List[AnnouncementPublic])
def get_club_announcements(club_id: int, db: Annotated[Session, Depends(get_session)]):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return sorted(club.announcements, key=lambda x: x.timestamp, reverse=True)