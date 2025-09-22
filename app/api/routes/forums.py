from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select, func
from app.db.database import get_session
from app.db.models import User, Club, Event
from app.api.deps import get_current_user

router = APIRouter()

# Pydantic models for forum functionality
class ForumPostCreate(BaseModel):
    title: str
    content: str
    club_id: Optional[int] = None
    event_id: Optional[int] = None
    category: str = "general"  # general, question, announcement, discussion

class ForumPostResponse(BaseModel):
    id: int
    title: str
    content: str
    author_name: str
    author_id: int
    club_id: Optional[int] = None
    event_id: Optional[int] = None
    category: str
    created_at: datetime
    replies_count: int = 0
    likes_count: int = 0

class ForumReplyCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None  # For nested replies

class ForumReplyResponse(BaseModel):
    id: int
    content: str
    author_name: str
    author_id: int
    post_id: int
    parent_id: Optional[int] = None
    created_at: datetime
    likes_count: int = 0

# In-memory storage for demo (replace with proper database models)
forum_posts = []
forum_replies = []
post_likes = []
reply_likes = []

@router.get("/posts", response_model=List[ForumPostResponse])
async def get_forum_posts(
    club_id: Optional[int] = None,
    event_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_session)] = None
):
    """Get forum posts with optional filtering"""
    
    # Filter posts based on parameters
    filtered_posts = forum_posts.copy()
    
    if club_id:
        filtered_posts = [p for p in filtered_posts if p.get('club_id') == club_id]
    if event_id:
        filtered_posts = [p for p in filtered_posts if p.get('event_id') == event_id]
    if category:
        filtered_posts = [p for p in filtered_posts if p.get('category') == category]
    
    # Sort by creation date (newest first)
    filtered_posts.sort(key=lambda x: x.get('created_at', datetime.now()), reverse=True)
    
    # Apply pagination
    paginated_posts = filtered_posts[offset:offset + limit]
    
    # Add reply counts
    for post in paginated_posts:
        post['replies_count'] = len([r for r in forum_replies if r.get('post_id') == post.get('id')])
        post['likes_count'] = len([l for l in post_likes if l.get('post_id') == post.get('id')])
    
    return paginated_posts

@router.post("/posts", response_model=ForumPostResponse)
async def create_forum_post(
    post_data: ForumPostCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Create a new forum post"""
    
    # Validate club/event exists if specified
    if post_data.club_id:
        club = db.get(Club, post_data.club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")
    
    if post_data.event_id:
        event = db.get(Event, post_data.event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
    
    # Create new post
    new_post = {
        'id': len(forum_posts) + 1,
        'title': post_data.title,
        'content': post_data.content,
        'author_name': current_user.full_name,
        'author_id': current_user.id,
        'club_id': post_data.club_id,
        'event_id': post_data.event_id,
        'category': post_data.category,
        'created_at': datetime.now(),
        'replies_count': 0,
        'likes_count': 0
    }
    
    forum_posts.append(new_post)
    return new_post

@router.get("/posts/{post_id}", response_model=ForumPostResponse)
async def get_forum_post(
    post_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """Get a specific forum post"""
    
    post = next((p for p in forum_posts if p.get('id') == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Add counts
    post['replies_count'] = len([r for r in forum_replies if r.get('post_id') == post_id])
    post['likes_count'] = len([l for l in post_likes if l.get('post_id') == post_id])
    
    return post

@router.get("/posts/{post_id}/replies", response_model=List[ForumReplyResponse])
async def get_post_replies(
    post_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """Get replies for a specific post"""
    
    # Check if post exists
    post = next((p for p in forum_posts if p.get('id') == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get replies for this post
    post_replies = [r for r in forum_replies if r.get('post_id') == post_id]
    
    # Add like counts
    for reply in post_replies:
        reply['likes_count'] = len([l for l in reply_likes if l.get('reply_id') == reply.get('id')])
    
    # Sort by creation date
    post_replies.sort(key=lambda x: x.get('created_at', datetime.now()))
    
    return post_replies

@router.post("/posts/{post_id}/replies", response_model=ForumReplyResponse)
async def create_reply(
    post_id: int,
    reply_data: ForumReplyCreate,
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Create a reply to a forum post"""
    
    # Check if post exists
    post = next((p for p in forum_posts if p.get('id') == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Create new reply
    new_reply = {
        'id': len(forum_replies) + 1,
        'content': reply_data.content,
        'author_name': current_user.full_name,
        'author_id': current_user.id,
        'post_id': post_id,
        'parent_id': reply_data.parent_id,
        'created_at': datetime.now(),
        'likes_count': 0
    }
    
    forum_replies.append(new_reply)
    return new_reply

@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Like or unlike a forum post"""
    
    # Check if post exists
    post = next((p for p in forum_posts if p.get('id') == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user already liked this post
    existing_like = next((l for l in post_likes if l.get('post_id') == post_id and l.get('user_id') == current_user.id), None)
    
    if existing_like:
        # Unlike
        post_likes.remove(existing_like)
        return {"message": "Post unliked", "liked": False}
    else:
        # Like
        new_like = {
            'post_id': post_id,
            'user_id': current_user.id,
            'created_at': datetime.now()
        }
        post_likes.append(new_like)
        return {"message": "Post liked", "liked": True}

@router.get("/categories")
async def get_forum_categories():
    """Get available forum categories"""
    return {
        "categories": [
            {"id": "general", "name": "General Discussion", "description": "General topics and conversations"},
            {"id": "question", "name": "Questions & Help", "description": "Ask questions and get help"},
            {"id": "announcement", "name": "Announcements", "description": "Important announcements and news"},
            {"id": "discussion", "name": "Club Discussions", "description": "Club-specific discussions"},
            {"id": "events", "name": "Event Discussions", "description": "Event-related conversations"}
        ]
    }
