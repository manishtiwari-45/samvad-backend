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
    administered_clubs: List["Club"] = Relationship(back_populates="admin")
    uploaded_gallery_photos: List["GalleryPhoto"] = Relationship(back_populates="uploader")

    coordinated_clubs: List["Club"] = Relationship(
        back_populates="coordinator",
        sa_relationship_kwargs={'foreign_keys': '[Club.coordinator_id]'}
    )
    sub_coordinated_clubs: List["Club"] = Relationship(
        back_populates="sub_coordinator",
        sa_relationship_kwargs={'foreign_keys': '[Club.sub_coordinator_id]'}
    )

# In app/db/models.py

class Club(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str
    
    # --- EXISTING/MODIFIED FIELDS ---
    admin_id: int = Field(foreign_key="user.id")
    cover_image_url: Optional[str] = Field(default=None)

    # --- NEW FIELDS ---
    category: Optional[str] = Field(default="General", index=True)
    contact_email: Optional[str] = Field(default=None)
    website_url: Optional[str] = Field(default=None)
    founded_date: Optional[datetime] = Field(default=None)
    
    # NEW: Link to users for coordinator roles
    coordinator_id: Optional[int] = Field(default=None, foreign_key="user.id")
    sub_coordinator_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # --- RELATIONSHIPS ---
    admin: User = Relationship(back_populates="administered_clubs")
    members: List[User] = Relationship(back_populates="clubs", link_model=Membership)
    events: List["Event"] = Relationship(back_populates="club")
    announcements: List["Announcement"] = Relationship(back_populates="club")

    # NEW: Define relationships for coordinators
    coordinator: Optional[User] = Relationship(
        back_populates="coordinated_clubs",
        sa_relationship_kwargs={'foreign_keys': '[Club.coordinator_id]'}
    )
    sub_coordinator: Optional[User] = Relationship(
        back_populates="sub_coordinated_clubs",
        sa_relationship_kwargs={'foreign_keys': '[Club.sub_coordinator_id]'}
    )

class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    date: datetime
    location: str
    club_id: int = Field(foreign_key="club.id")
    
    # Relationships
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

# Add this new class at the end of app/db/models.py

class GalleryPhoto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_url: str = Field(..., description="URL of the photo hosted on Cloudinary")
    public_id: str = Field(..., description="Public ID from Cloudinary for managing the asset")
    caption: Optional[str] = Field(default=None)
    uploaded_by_id: int = Field(foreign_key="user.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # This creates a link to the User model so we can see who uploaded the photo
    uploader: "User" = Relationship()