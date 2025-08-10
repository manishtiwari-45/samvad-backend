from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel
import face_recognition
import numpy as np
import io
from PIL import Image

from app.core.security import get_password_hash, verify_password, create_access_token
from app.db.database import get_session
from app.db.models import User, UserRole, Club
from app.api.deps import get_current_user
from app.schemas import UserPublic, ClubPublic, UserPublicWithDetails, ClubAdminView 

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
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    user = User.model_validate(user_in, update={"hashed_password": get_password_hash(user_in.password)})
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

@router.get("/me/administered-clubs", response_model=List[ClubAdminView])
def get_my_administered_clubs(
    current_user: Annotated[User, Depends(get_current_user)],
):
    clubs_with_counts = []
    for club in current_user.administered_clubs:
        club_view = ClubAdminView(
            id=club.id, name=club.name, description=club.description,
            admin_id=club.admin_id, admin=club.admin,
            member_count=len(club.members), event_count=len(club.events)
        )
        clubs_with_counts.append(club_view)
    return clubs_with_counts

# --- NAYA ENDPOINT: FACE ENROLLMENT KE LIYE ---
@router.post("/me/enroll-face", response_model=UserPublic)
async def enroll_user_face(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    file: UploadFile = File(...),
):
    """
    Enrolls the current user's face by processing an uploaded image.
    """
    # 1. Image ko memory mein read karein
    contents = await file.read()
    
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image_np = np.array(image)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    # 2. Face locations aur encodings find karein
    face_locations = face_recognition.face_locations(image_np)
    if not face_locations:
        raise HTTPException(status_code=400, detail="No face found in the image.")
    if len(face_locations) > 1:
        raise HTTPException(status_code=400, detail="Multiple faces found. Please upload an image with only one face.")
    
    # 3. Pehla (aur eklauta) face encoding get karein
    face_encoding = face_recognition.face_encodings(image_np, known_face_locations=face_locations)[0]

    # 4. Numpy array ko ek string mein convert karein taaki database mein save ho sake
    encoding_str = ",".join(map(str, face_encoding))

    # 5. User model mein save karein
    user_to_update = db.get(User, current_user.id)
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_to_update.face_encoding = encoding_str
    db.add(user_to_update)
    db.commit()
    db.refresh(user_to_update)

    return user_to_update