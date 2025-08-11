from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Annotated
from sqlmodel import Session
import random
from twilio.rest import Client

from app.core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
from app.db.database import get_session
from app.db.models import User
from app.api.deps import get_current_user

router = APIRouter()

# Simple in-memory storage for OTPs. For production, use Redis or a database.
otp_storage = {}

# Initialize Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

class PhonePayload(BaseModel):
    whatsapp_number: str

class OTPPayload(BaseModel):
    otp: str

@router.post("/send-otp", status_code=status.HTTP_200_OK)
def send_otp(payload: PhonePayload, db: Annotated[Session, Depends(get_session)]):
    otp = random.randint(100000, 999999)
    phone_number_e164 = payload.whatsapp_number
    
    # Store the OTP
    otp_storage[phone_number_e164] = otp
    print(f"Generated OTP for {phone_number_e164}: {otp}") # For debugging

    try:
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=f"Your CampusConnect verification code is: {otp}",
            to=f"whatsapp:{phone_number_e164}"
        )
        return {"message": "OTP sent successfully."}
    except Exception as e:
        print(f"Twilio Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP.")

@router.post("/verify-otp", status_code=status.HTTP_200_OK)
def verify_otp(
    payload: OTPPayload,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)]
):
    user = db.get(User, current_user.id)
    if not user or not user.whatsapp_number:
        raise HTTPException(status_code=404, detail="User or WhatsApp number not found.")

    stored_otp = otp_storage.get(user.whatsapp_number)
    if not stored_otp or stored_otp != int(payload.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")
    
    # Mark user as verified
    user.whatsapp_verified = True
    db.add(user)
    db.commit()
    
    # Clean up OTP
    del otp_storage[user.whatsapp_number]
    
    return {"message": "WhatsApp number verified successfully."}