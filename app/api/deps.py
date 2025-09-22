from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select
from app.db.models import User, UserRole

from app.core.config import JWT_SECRET_KEY, ALGORITHM
from app.db.database import get_session
from app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_session)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception
    return user

# Authorization Dependencies
def get_super_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency to ensure the user has the 'super_admin' role.
    SuperAdmin: Overall head/mentor responsible for managing admins and system-wide operations.
    """
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SuperAdmin access required",
        )
    return current_user

def get_admin_or_super_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency to ensure the user has 'club_admin' or 'super_admin' role.
    Admin: Can manage clubs and events. SuperAdmin: System-wide management.
    """
    if current_user.role not in [UserRole.club_admin, UserRole.super_admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or SuperAdmin access required",
        )
    return current_user

def get_club_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency to ensure the user has the 'club_admin' role.
    Admin: Responsible for club and event management, can act as coordinators.
    """
    if current_user.role != UserRole.club_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Club Admin access required",
        )
    return current_user