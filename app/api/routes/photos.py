from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime
import cloudinary
import cloudinary.uploader

from app.core.cloudinary_utils import upload_to_cloudinary
from app.core.secure_error_handler import SecureErrorHandler, SecureValidator
from app.db.database import get_session
from app.db.models import EventPhoto, GalleryPhoto, User, UserRole, Event
from app.api.deps import get_current_user, get_super_admin
from app.schemas import EventPhotoPublic, GalleryPhotoPublic # Import the new schema
from app.core.cloudinary_utils import upload_to_cloudinary # Import the Cloudinary helper

router = APIRouter()

# ===============================================================
# === EVENT-SPECIFIC PHOTOS (Existing Endpoints) ==============
# ===============================================================

class EventInfo(BaseModel):
    id: int
    name: str

class PhotoWithDetails(BaseModel):
    id: int
    image_url: str
    timestamp: datetime
    event: EventInfo

@router.get("/", response_model=List[PhotoWithDetails], summary="Get All Event Photos")
def get_all_photos(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get all photos from all specific club events, sorted by most recent.
    """
    photos = db.exec(select(EventPhoto).order_by(EventPhoto.timestamp.desc())).all()
    return photos

@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an Event Photo")
def delete_photo(
    photo_id: int,
    db: Annotated[Session, Depends(get_session)],
    super_admin: Annotated[User, Depends(get_super_admin)],
):
    """
    Delete a photo by its ID from a specific event. (Super Admin only)
    """
    photo_to_delete = db.get(EventPhoto, photo_id)
    if not photo_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event photo not found")

    try:
        cloudinary.uploader.destroy(photo_to_delete.public_id)
    except Exception as e:
        SecureErrorHandler.log_error(e, f"Cloudinary photo deletion {photo_id}")

    db.delete(photo_to_delete)
    db.commit()
    return None

# ===============================================================
# === COMMON GALLERY PHOTOS (New Endpoints) =====================
# ===============================================================

@router.post("/gallery", response_model=GalleryPhotoPublic, status_code=status.HTTP_201_CREATED, summary="Upload to Common Gallery")
def upload_to_gallery(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(..., description="The photo to upload."),
    caption: Optional[str] = Form(None, description="An optional caption for the photo.")
):
    """
    Upload a photo to the common gallery.
    Allowed for Super Admins and Club Admins.
    """
    if current_user.role not in [UserRole.super_admin, UserRole.club_admin]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to upload to the gallery.")

    upload_result = upload_to_cloudinary(file, folder="stellurhub_gallery")
    
    new_photo = GalleryPhoto(
        image_url=upload_result['secure_url'],
        public_id=upload_result['public_id'],
        caption=caption,
        uploader=current_user
    )
    
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)
    
    return new_photo

@router.get("/gallery", response_model=List[GalleryPhotoPublic], summary="Get All Common Gallery Photos")
def get_common_gallery_photos(
    db: Annotated[Session, Depends(get_session)]
):
    """
    Get all photos from the common gallery, available to all users.
    """
    photos = db.exec(select(GalleryPhoto).order_by(GalleryPhoto.timestamp.desc())).all()
    return photos

@router.delete("/gallery/{photo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a Common Gallery Photo")
def delete_gallery_photo(
    photo_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Delete a photo from the common gallery.
    Allowed for Super Admins (can delete any) and Club Admins (can delete their own).
    """
    photo = db.get(GalleryPhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery photo not found")

    # Check permissions
    is_super_admin = current_user.role == UserRole.super_admin
    is_uploader = photo.uploaded_by_id == current_user.id

    if not (is_super_admin or is_uploader):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this photo.")

    try:
        cloudinary.uploader.destroy(photo.public_id)
    except Exception as e:
        SecureErrorHandler.log_error(e, f"Cloudinary gallery photo deletion {photo_id}")

    db.delete(photo)
    db.commit()
    return None