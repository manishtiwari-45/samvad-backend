from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel
# import face_recognition  # Temporarily disabled for deployment
# import numpy as np  # Temporarily disabled for deployment
import io
from PIL import Image
import requests

from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.super_admin_config import is_super_admin_email, log_super_admin_attempt
from app.core.secure_error_handler import SecureErrorHandler, SecureValidator
from app.db.database import get_session
from app.db.models import User, UserRole, Club
from app.api.deps import get_current_user
from app.schemas import UserPublic, ClubPublic, UserPublicWithDetails, ClubAdminView

def get_user_role_by_email(email: str) -> UserRole:
    """
    Determine user role based on email address.
    Super Admin emails get super_admin role, everyone else gets student role.
    """
    is_super_admin = is_super_admin_email(email)
    log_super_admin_attempt(email, is_super_admin)
    
    if is_super_admin:
        return UserRole.super_admin
    return UserRole.student 

# --- Define Local Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    whatsapp_number: str
    whatsapp_consent: bool
    # Role is removed - all new users are students by default

class GoogleLoginRequest(BaseModel):
    token: str
    # Role is removed - all new users are students by default

# --- Router ---
router = APIRouter()

@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Annotated[Session, Depends(get_session)]):
    # Email domain restriction removed - now accepts all email domains
    
    existing_user_email = db.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user_email:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # --- WHATSAPP NUMBER CHECK WALA CODE YAHAN SE HATA DIYA GAYA HAI ---
    # existing_user_whatsapp = db.exec(select(User).where(User.whatsapp_number == user_in.whatsapp_number)).first()
    # if existing_user_whatsapp:
    #     raise HTTPException(status_code=400, detail="This WhatsApp number is already registered.")

    # Assign role based on email whitelist - Super Admin for whitelisted emails, Student for others
    assigned_role = get_user_role_by_email(user_in.email)
    user = User.model_validate(user_in, update={
        "hashed_password": get_password_hash(user_in.password),
        "role": assigned_role  # Super Admin for whitelisted emails, Student for others
    })
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_session)],
):
    # Email domain restriction removed - now accepts all email domains
    
    user = db.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/google-login", response_model=Token)
def google_login(request: GoogleLoginRequest, db: Annotated[Session, Depends(get_session)]):
    try:
        # Verify the Google token by calling Google's API
        # Try both userinfo endpoints for better compatibility
        response = requests.get(
            f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={request.token}"
        )
        
        # If first endpoint fails, try the v2 endpoint
        if response.status_code != 200:
            response = requests.get(
                f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={request.token}"
            )
        
        if response.status_code != 200:
            print(f"Google API Error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
        
        google_user_data = response.json()
        print(f"Google user data received: {google_user_data}")  # Debug logging
        
        email = google_user_data.get("email")
        name = google_user_data.get("name")
        
        if not email:
            print(f"No email found in Google response: {google_user_data}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not retrieve email from Google"
            )
        
        # Email domain restriction removed - now accepts all email domains
        
        # Check if user exists, if not create them
        user = db.exec(select(User).where(User.email == email)).first()
        if not user:
            # Create new user with Google data - role based on email whitelist
            assigned_role = get_user_role_by_email(email)
            user = User(
                email=email,
                full_name=name or email.split("@")[0],
                hashed_password=get_password_hash("google_oauth_user"),  # Placeholder password
                role=assigned_role,  # Super Admin for whitelisted emails, Student for others
                whatsapp_number="",  # Empty for Google users
                whatsapp_consent=False
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
        
    except requests.RequestException as e:
        print(f"Request exception during Google login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify Google token"
        )
    except Exception as e:
        print(f"Unexpected error during Google login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please check your credentials and try again."
        )

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

# Face enrollment temporarily disabled for deployment
# @router.post("/me/enroll-face", response_model=UserPublic)
# async def enroll_user_face(
#     current_user: Annotated[User, Depends(get_current_user)],
#     db: Annotated[Session, Depends(get_session)],
#     file: UploadFile = File(...),
# ):
#     try:
#         # Validate file first
#         SecureValidator.validate_file_upload(file)
#         
#         contents = await file.read()
#         image = Image.open(io.BytesIO(contents)).convert("RGB")
#         image_np = np.array(image)
#     except HTTPException:
#         # Re-raise validation errors
#         raise
#     except Exception as e:
#         raise SecureErrorHandler.handle_validation_error("image", "Invalid image file format")

#     face_locations = face_recognition.face_locations(image_np)
#     if not face_locations:
#         raise HTTPException(status_code=400, detail="No face found in the image.")
#     if len(face_locations) > 1:
#         raise HTTPException(status_code=400, detail="Multiple faces found. Please upload an image with only one face.")
    
#     face_encoding = face_recognition.face_encodings(image_np, known_face_locations=face_locations)[0]
#     encoding_str = ",".join(map(str, face_encoding))
    
#     user_to_update = db.get(User, current_user.id)
#     if not user_to_update:
#         raise HTTPException(status_code=404, detail="User not found")
        
#     user_to_update.face_encoding = encoding_str
#     db.add(user_to_update)
#     db.commit()
#     db.refresh(user_to_update)
#     return user_to_update