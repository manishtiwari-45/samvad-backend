from typing import List, Optional
from enum import Enum
from sqlmodel import Field, Relationship, SQLModel
from datetime import datetime

# --- Enums and Link Models ---

class UserRole(str, Enum):
    student = "student"
    club_admin = "club_admin"
    super_admin = "super_admin"

class Membership(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    club_id: int = Field(foreign_key="club.id", primary_key=True)

class EventRegistration(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    event_id: int = Field(foreign_key="event.id", primary_key=True)

# --- Main Models ---

# NOTE: The forward reference "class Club;" has been removed as it was causing a SyntaxError.
# Type hints using strings like List["Club"] handle this correctly.

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    hashed_password: str
    role: UserRole = Field(default=UserRole.student)
    face_encoding: Optional[str] = Field(default=None, max_length=4096)
    whatsapp_number: Optional[str] = Field(default=None, index=True)
    whatsapp_verified: bool = Field(default=False)
    whatsapp_consent: bool = Field(default=False)
    
    # Relationships
    clubs: List["Club"] = Relationship(back_populates="members", link_model=Membership)
    events_attending: List["Event"] = Relationship(back_populates="attendees", link_model=EventRegistration)
    
    administered_clubs: List["Club"] = Relationship(
        back_populates="admin",
        sa_relationship_kwargs={'foreign_keys': '[Club.admin_id]'}
    )
    coordinated_clubs: List["Club"] = Relationship(
        back_populates="coordinator",
        sa_relationship_kwargs={'foreign_keys': '[Club.coordinator_id]'}
    )
    sub_coordinated_clubs: List["Club"] = Relationship(
        back_populates="sub_coordinator",
        sa_relationship_kwargs={'foreign_keys': '[Club.sub_coordinator_id]'}
    )
    uploaded_gallery_photos: List["GalleryPhoto"] = Relationship(back_populates="uploader")
    role_requests: List["RoleRequest"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={'foreign_keys': '[RoleRequest.user_id]'}
    )
    reviewed_role_requests: List["RoleRequest"] = Relationship(
        back_populates="reviewed_by",
        sa_relationship_kwargs={'foreign_keys': '[RoleRequest.reviewed_by_id]'}
    )


class Club(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str
    
    admin_id: int = Field(foreign_key="user.id")
    cover_image_url: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default="General", index=True)
    contact_email: Optional[str] = Field(default=None)
    website_url: Optional[str] = Field(default=None)
    founded_date: Optional[datetime] = Field(default=None)
    
    coordinator_id: Optional[int] = Field(default=None, foreign_key="user.id")
    sub_coordinator_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Relationships
    admin: "User" = Relationship(
        back_populates="administered_clubs",
        sa_relationship_kwargs={'foreign_keys': '[Club.admin_id]'}
    )
    coordinator: Optional["User"] = Relationship(
        back_populates="coordinated_clubs",
        sa_relationship_kwargs={'foreign_keys': '[Club.coordinator_id]'}
    )
    sub_coordinator: Optional["User"] = Relationship(
        back_populates="sub_coordinated_clubs",
        sa_relationship_kwargs={'foreign_keys': '[Club.sub_coordinator_id]'}
    )
    
    members: List["User"] = Relationship(back_populates="clubs", link_model=Membership)
    events: List["Event"] = Relationship(back_populates="club")
    announcements: List["Announcement"] = Relationship(back_populates="club")


# ... (The rest of your models: Event, Announcement, etc. remain the same) ...

class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    date: datetime
    location: str
    club_id: int = Field(foreign_key="club.id")
    
    club: Club = Relationship(back_populates="events")
    attendees: List[User] = Relationship(back_populates="events_attending", link_model=EventRegistration)
    photos: List["EventPhoto"] = Relationship(back_populates="event") 

class Announcement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    club_id: int = Field(foreign_key="club.id")
    club: Club = Relationship(back_populates="announcements")

class EventPhoto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_url: str
    public_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    event_id: int = Field(foreign_key="event.id")
    event: Event = Relationship(back_populates="photos")

class AttendanceRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(default=None)
    user_id: int = Field(foreign_key="user.id")
    event_id: Optional[int] = Field(default=None, foreign_key="event.id")

class GalleryPhoto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_url: str
    public_id: str
    caption: Optional[str] = Field(default=None)
    uploaded_by_id: int = Field(foreign_key="user.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    uploader: "User" = Relationship(back_populates="uploaded_gallery_photos")

class RoleRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class RoleRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    requested_role: UserRole = Field(index=True)
    current_role: UserRole = Field(index=True)
    reason: str = Field(max_length=1000)  # User's reason for requesting the role
    status: RoleRequestStatus = Field(default=RoleRequestStatus.pending, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    reviewed_at: Optional[datetime] = Field(default=None)
    reviewed_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    admin_notes: Optional[str] = Field(default=None, max_length=1000)  # Admin's notes on the decision
    
    # Relationships
    user: "User" = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[RoleRequest.user_id]'}
    )
    reviewed_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[RoleRequest.reviewed_by_id]'}
    )
