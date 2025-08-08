from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.db.models import UserRole

# --- User Schemas ---
class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole

# --- Club Schemas ---
class ClubBase(BaseModel):
    name: str
    description: str

class ClubCreate(ClubBase):
    pass

class ClubPublic(ClubBase):
    id: int
    admin_id: int
    admin: UserPublic

# --- Event Schemas ---
class EventBase(BaseModel):
    name: str
    description: str
    date: datetime
    location: str

class EventCreate(EventBase):
    pass

class EventPublic(EventBase):
    id: int
    club_id: int

# --- Announcement Schemas ---
class AnnouncementBase(BaseModel):
    title: str
    content: str

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementPublic(AnnouncementBase):
    id: int
    timestamp: datetime
    club_id: int

# --- Schemas for Detailed Views ---
class ClubPublicForUser(BaseModel):
    id: int
    name: str
    description: str

class EventPublicForUser(BaseModel):
    id: int
    name: str
    date: datetime

class UserPublicWithDetails(UserPublic):
    clubs: List[ClubPublicForUser] = []
    events_attending: List[EventPublicForUser] = []

class ClubWithMembersAndEvents(ClubPublic):
    members: List[UserPublic] = []
    events: List[EventPublic] = []

class DashboardStats(BaseModel):
    total_users: int
    active_clubs: int
    total_events: int
    pending_clubs: int = 0 

# Update any forward references if needed (though not strictly necessary here)
ClubWithMembersAndEvents.model_rebuild()