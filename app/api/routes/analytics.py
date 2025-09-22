from datetime import datetime, timedelta
from typing import Annotated, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from app.db.database import get_session
from app.db.models import User, Club, Event, Membership, EventRegistration, Announcement
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Get overall dashboard statistics"""
    
    # Total counts
    total_users = db.exec(select(func.count(User.id))).first()
    total_clubs = db.exec(select(func.count(Club.id))).first()
    total_events = db.exec(select(func.count(Event.id))).first()
    
    # Active events (future events)
    active_events = db.exec(
        select(func.count(Event.id)).where(Event.date >= datetime.now())
    ).first()
    
    # Recent registrations (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_users = db.exec(
        select(func.count(User.id)).where(User.id >= 1)  # Assuming auto-increment IDs
    ).first()
    
    # Most popular clubs (by member count)
    popular_clubs = db.exec(
        select(Club.name, func.count(Membership.user_id).label('member_count'))
        .join(Membership, Club.id == Membership.club_id, isouter=True)
        .group_by(Club.id, Club.name)
        .order_by(func.count(Membership.user_id).desc())
        .limit(5)
    ).all()
    
    # Upcoming events with registration counts
    upcoming_events = db.exec(
        select(Event.name, Event.date, func.count(EventRegistration.user_id).label('registrations'))
        .join(EventRegistration, Event.id == EventRegistration.event_id, isouter=True)
        .where(Event.date >= datetime.now())
        .group_by(Event.id, Event.name, Event.date)
        .order_by(Event.date)
        .limit(5)
    ).all()
    
    return {
        "totals": {
            "users": total_users or 0,
            "clubs": total_clubs or 0,
            "events": total_events or 0,
            "active_events": active_events or 0
        },
        "popular_clubs": [
            {"name": club.name, "members": club.member_count or 0} 
            for club in popular_clubs
        ],
        "upcoming_events": [
            {
                "name": event.name, 
                "date": event.date.isoformat(), 
                "registrations": event.registrations or 0
            } 
            for event in upcoming_events
        ]
    }

@router.get("/club-analytics/{club_id}")
async def get_club_analytics(
    club_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Get analytics for a specific club"""
    
    # Verify club exists and user has access
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    # Member count over time (simplified - just current count)
    member_count = db.exec(
        select(func.count(Membership.user_id)).where(Membership.club_id == club_id)
    ).first()
    
    # Events hosted by this club
    club_events = db.exec(
        select(Event.name, Event.date, func.count(EventRegistration.user_id).label('registrations'))
        .join(EventRegistration, Event.id == EventRegistration.event_id, isouter=True)
        .where(Event.club_id == club_id)
        .group_by(Event.id, Event.name, Event.date)
        .order_by(Event.date.desc())
        .limit(10)
    ).all()
    
    # Recent announcements count
    announcements_count = db.exec(
        select(func.count(Announcement.id)).where(Announcement.club_id == club_id)
    ).first()
    
    return {
        "club_name": club.name,
        "member_count": member_count or 0,
        "total_events": len(club_events),
        "announcements_count": announcements_count or 0,
        "recent_events": [
            {
                "name": event.name,
                "date": event.date.isoformat(),
                "registrations": event.registrations or 0
            }
            for event in club_events
        ]
    }

@router.get("/user-activity")
async def get_user_activity(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Get current user's activity statistics"""
    
    # User's club memberships
    user_clubs = db.exec(
        select(Club.name)
        .join(Membership, Club.id == Membership.club_id)
        .where(Membership.user_id == current_user.id)
    ).all()
    
    # User's event registrations
    user_events = db.exec(
        select(Event.name, Event.date)
        .join(EventRegistration, Event.id == EventRegistration.event_id)
        .where(EventRegistration.user_id == current_user.id)
        .where(Event.date >= datetime.now())
        .order_by(Event.date)
    ).all()
    
    return {
        "clubs_joined": len(user_clubs),
        "upcoming_events": len(user_events),
        "clubs": [club.name for club in user_clubs],
        "events": [
            {"name": event.name, "date": event.date.isoformat()}
            for event in user_events
        ]
    }
