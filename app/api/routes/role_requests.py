from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_session
from app.db.models import User, UserRole, RoleRequest, RoleRequestStatus
from app.api.deps import get_current_user
from app.schemas import UserPublic

# --- Schemas ---
class RoleRequestCreate(BaseModel):
    requested_role: UserRole
    reason: str

class RoleRequestResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    requested_role: UserRole
    current_role: UserRole
    reason: str
    status: RoleRequestStatus
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by_name: str | None = None
    admin_notes: str | None = None

class RoleRequestReview(BaseModel):
    status: RoleRequestStatus  # approved or rejected
    admin_notes: str | None = None

# --- Router ---
router = APIRouter()

@router.post("/request-role", response_model=dict)
def request_role_upgrade(
    request_data: RoleRequestCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Allow students to request role upgrades to club_admin"""
    
    # Security checks
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can request role upgrades"
        )
    
    if request_data.requested_role == UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a student"
        )
    
    if request_data.requested_role == UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin role cannot be requested"
        )
    
    if request_data.requested_role != UserRole.club_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only club admin role can be requested"
        )
    
    # Check if user already has a pending request
    existing_request = db.exec(
        select(RoleRequest).where(
            RoleRequest.user_id == current_user.id,
            RoleRequest.status == RoleRequestStatus.pending
        )
    ).first()
    
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending role request"
        )
    
    # Create the role request
    role_request = RoleRequest(
        user_id=current_user.id,
        requested_role=request_data.requested_role,
        current_role=current_user.role,
        reason=request_data.reason,
        status=RoleRequestStatus.pending
    )
    
    db.add(role_request)
    db.commit()
    db.refresh(role_request)
    
    return {
        "message": "Role request submitted successfully",
        "request_id": role_request.id,
        "status": "pending"
    }

@router.get("/my-requests", response_model=List[RoleRequestResponse])
def get_my_role_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Get current user's role requests"""
    
    requests = db.exec(
        select(RoleRequest).where(RoleRequest.user_id == current_user.id)
        .order_by(RoleRequest.created_at.desc())
    ).all()
    
    result = []
    for req in requests:
        reviewed_by_name = None
        if req.reviewed_by_id:
            reviewer = db.get(User, req.reviewed_by_id)
            reviewed_by_name = reviewer.full_name if reviewer else None
        
        result.append(RoleRequestResponse(
            id=req.id,
            user_id=req.user_id,
            user_name=current_user.full_name,
            user_email=current_user.email,
            requested_role=req.requested_role,
            current_role=req.current_role,
            reason=req.reason,
            status=req.status,
            created_at=req.created_at,
            reviewed_at=req.reviewed_at,
            reviewed_by_name=reviewed_by_name,
            admin_notes=req.admin_notes
        ))
    
    return result

@router.get("/all-requests", response_model=List[RoleRequestResponse])
def get_all_role_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Get all role requests - only for super admins"""
    
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can view all role requests"
        )
    
    requests = db.exec(
        select(RoleRequest).order_by(RoleRequest.created_at.desc())
    ).all()
    
    result = []
    for req in requests:
        user = db.get(User, req.user_id)
        reviewed_by_name = None
        if req.reviewed_by_id:
            reviewer = db.get(User, req.reviewed_by_id)
            reviewed_by_name = reviewer.full_name if reviewer else None
        
        result.append(RoleRequestResponse(
            id=req.id,
            user_id=req.user_id,
            user_name=user.full_name if user else "Unknown",
            user_email=user.email if user else "Unknown",
            requested_role=req.requested_role,
            current_role=req.current_role,
            reason=req.reason,
            status=req.status,
            created_at=req.created_at,
            reviewed_at=req.reviewed_at,
            reviewed_by_name=reviewed_by_name,
            admin_notes=req.admin_notes
        ))
    
    return result

@router.get("/pending-requests", response_model=List[RoleRequestResponse])
def get_pending_role_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Get pending role requests - only for super admins"""
    
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can view pending role requests"
        )
    
    requests = db.exec(
        select(RoleRequest).where(RoleRequest.status == RoleRequestStatus.pending)
        .order_by(RoleRequest.created_at.desc())
    ).all()
    
    result = []
    for req in requests:
        user = db.get(User, req.user_id)
        
        result.append(RoleRequestResponse(
            id=req.id,
            user_id=req.user_id,
            user_name=user.full_name if user else "Unknown",
            user_email=user.email if user else "Unknown",
            requested_role=req.requested_role,
            current_role=req.current_role,
            reason=req.reason,
            status=req.status,
            created_at=req.created_at,
            reviewed_at=req.reviewed_at,
            reviewed_by_name=None,
            admin_notes=req.admin_notes
        ))
    
    return result

@router.post("/review-request/{request_id}", response_model=dict)
def review_role_request(
    request_id: int,
    review_data: RoleRequestReview,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Review a role request - only for super admins"""
    
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can review role requests"
        )
    
    if review_data.status not in [RoleRequestStatus.approved, RoleRequestStatus.rejected]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be either 'approved' or 'rejected'"
        )
    
    # Get the role request
    role_request = db.get(RoleRequest, request_id)
    if not role_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role request not found"
        )
    
    if role_request.status != RoleRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request has already been reviewed"
        )
    
    # Update the role request
    role_request.status = review_data.status
    role_request.reviewed_at = datetime.utcnow()
    role_request.reviewed_by_id = current_user.id
    role_request.admin_notes = review_data.admin_notes
    
    # If approved, update the user's role
    if review_data.status == RoleRequestStatus.approved:
        user = db.get(User, role_request.user_id)
        if user:
            user.role = role_request.requested_role
            db.add(user)
    
    db.add(role_request)
    db.commit()
    
    action = "approved" if review_data.status == RoleRequestStatus.approved else "rejected"
    return {
        "message": f"Role request {action} successfully",
        "request_id": request_id,
        "status": review_data.status
    }

@router.delete("/cancel-request/{request_id}", response_model=dict)
def cancel_role_request(
    request_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    """Cancel a pending role request - only the requester can cancel their own request"""
    
    role_request = db.get(RoleRequest, request_id)
    if not role_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role request not found"
        )
    
    if role_request.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own role requests"
        )
    
    if role_request.status != RoleRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be cancelled"
        )
    
    db.delete(role_request)
    db.commit()
    
    return {
        "message": "Role request cancelled successfully",
        "request_id": request_id
    }
