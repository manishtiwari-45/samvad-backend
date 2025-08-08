from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.database import get_session
from app.db.models import Club, User, UserRole, Membership, Announcement
from app.api.deps import get_current_user
from app.schemas import ClubCreate, ClubPublic, ClubWithMembersAndEvents, UserPublic, AnnouncementCreate, AnnouncementPublic

router = APIRouter()

# --- CRUD for Clubs ---
@router.post("/", response_model=ClubPublic, status_code=status.HTTP_201_CREATED)
def create_club(
    club_in: ClubCreate,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.role not in [UserRole.club_admin, UserRole.super_admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can create clubs."
        )

    club = Club.model_validate(club_in, update={"admin_id": current_user.id})
    db.add(club)
    db.commit()
    db.refresh(club)
    
    membership = Membership(user_id=current_user.id, club_id=club.id)
    db.add(membership)
    db.commit()
    
    db.refresh(club)
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

@router.get("/", response_model=List[ClubPublic])
def get_all_clubs(db: Annotated[Session, Depends(get_session)]):
    return db.exec(select(Club)).all()

@router.get("/{club_id}", response_model=ClubWithMembersAndEvents)
def get_club_by_id(club_id: int, db: Annotated[Session, Depends(get_session)]):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    return club

# --- Club Membership Management ---
@router.post("/{club_id}/join", response_model=UserPublic)
def join_club(
    club_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    existing_membership = db.exec(select(Membership).where(Membership.user_id == current_user.id, Membership.club_id == club_id)).first()
    if existing_membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member of this club")
    membership = Membership(user_id=current_user.id, club_id=club_id)
    db.add(membership)
    db.commit()
    return current_user

# --- Club Announcements ---
@router.post("/{club_id}/announcements", response_model=AnnouncementPublic, status_code=status.HTTP_201_CREATED)
def create_announcement_for_club(
    club_id: int,
    announcement_in: AnnouncementCreate,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    if club.admin_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the club admin can post announcements")
    announcement = Announcement.model_validate(announcement_in, update={"club_id": club_id})
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement

@router.get("/{club_id}/announcements", response_model=List[AnnouncementPublic])
def get_club_announcements(club_id: int, db: Annotated[Session, Depends(get_session)]):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return sorted(club.announcements, key=lambda x: x.timestamp, reverse=True)