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
    """
    Create a new club. The user creating the club automatically becomes its admin.
    """
    if current_user.role == UserRole.student:
        current_user.role = UserRole.club_admin
        db.add(current_user)

    club = Club.model_validate(club_in, update={"admin_id": current_user.id})
    db.add(club)
    db.commit()
    db.refresh(club)
    
    membership = Membership(user_id=current_user.id, club_id=club.id)
    db.add(membership)
    db.commit()
    
    db.refresh(club)
    return club

@router.get("/", response_model=List[ClubPublic])
def get_all_clubs(db: Annotated[Session, Depends(get_session)]):
    """Get a list of all clubs."""
    return db.exec(select(Club)).all()

@router.get("/{club_id}", response_model=ClubWithMembersAndEvents)
def get_club_by_id(club_id: int, db: Annotated[Session, Depends(get_session)]):
    """Get detailed information about a single club, including members and events."""
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
    """Allows the current user to join a club."""
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")

    existing_membership = db.exec(
        select(Membership).where(Membership.user_id == current_user.id, Membership.club_id == club_id)
    ).first()
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
    """Post a new announcement for a club. Only the club admin can do this."""
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