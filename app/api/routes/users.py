from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.security import get_password_hash, verify_password, create_access_token
from app.db.database import get_session
from app.db.models import User, UserRole, Club
from app.api.deps import get_current_user
# Corrected import: 'UserCreate' is removed from this line
from app.schemas import UserPublic, ClubPublic, UserPublicWithDetails

# --- Define Local Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole = UserRole.student

# --- Router ---

router = APIRouter()

@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Annotated[Session, Depends(get_session)]):
    existing_user = db.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    hashed_password = get_password_hash(user_in.password)
    user = User.model_validate(user_in, update={"hashed_password": hashed_password})
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_session)],
):
    user = db.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserPublicWithDetails)
def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

@router.get("/me/administered-clubs", response_model=List[ClubPublic])
def get_my_administered_clubs(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user.administered_clubs