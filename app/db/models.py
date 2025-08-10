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
    
    # Relationships
    clubs: List["Club"] = Relationship(back_populates="members", link_model=Membership)
    events_attending: List["Event"] = Relationship(back_populates="attendees", link_model=EventRegistration)
    administered_clubs: List["Club"] = Relationship(back_populates="admin")

class Club(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str
    admin_id: int = Field(foreign_key="user.id")
    
    # Relationships
    admin: User = Relationship(back_populates="administered_clubs")
    members: List[User] = Relationship(back_populates="clubs", link_model=Membership)
    events: List["Event"] = Relationship(back_populates="club")
    announcements: List["Announcement"] = Relationship(back_populates="club")

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

# --- ATTENDANCE TABLE KO UPDATE KIYA GAYA HAI ---
class AttendanceRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(default=None) # Naya notes field
    
    user_id: int = Field(foreign_key="user.id")
    # event_id ab zaroori nahi hai
    event_id: Optional[int] = Field(default=None, foreign_key="event.id")