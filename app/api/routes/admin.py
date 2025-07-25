from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.database import get_session
from app.db.models import User, UserRole
from app.api.deps import get_super_admin
from app.schemas import UserPublic

router = APIRouter()

@router.get("/users", response_model=List[UserPublic])
def get_all_users(
    db: Annotated[Session, Depends(get_session)],
    super_admin: Annotated[User, Depends(get_super_admin)],
):
    """
    Get a list of all users. (Super Admin only)
    """
    return db.exec(select(User)).all()


@router.put("/users/{user_id}/role", response_model=UserPublic)
def update_user_role(
    user_id: int,
    new_role: UserRole,
    db: Annotated[Session, Depends(get_session)],
    super_admin: Annotated[User, Depends(get_super_admin)],
):
    """
    Update a user's role. (Super Admin only)
    """
    user_to_update = db.get(User, user_id)
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user_to_update.role = new_role
    db.add(user_to_update)
    db.commit()
    db.refresh(user_to_update)
    return user_to_update


@router.delete("/users/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_session)],
    super_admin: Annotated[User, Depends(get_super_admin)],
):
    """
    Delete a user. (Super Admin only)
    """
    user_to_delete = db.get(User, user_id)
    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Prevent super admin from deleting themselves
    if user_to_delete.id == super_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Super admin cannot delete themselves")
        
    db.delete(user_to_delete)
    db.commit()
    return {"message": f"User with ID {user_id} deleted successfully."}