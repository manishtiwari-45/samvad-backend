from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Annotated
from sqlmodel import Session
import random
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
from app.db.database import get_session
from app.db.models import User
from app.api.deps import get_current_user

router = APIRouter()

# Simple in-memory storage for OTPs. For production, use Redis or a database.
otp_storage = {}

# Initialize Twilio Client safely
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except Exception as e:
        print(f"Failed to initialize Twilio client: {e}")
else:
    print("Twilio credentials not found. OTP service will be disabled.")


class PhonePayload(BaseModel):
    whatsapp_number: str

class OTPPayload(BaseModel):
    otp: str

@router.post("/send-otp", status_code=status.HTTP_200_OK)
def send_otp(payload: PhonePayload, db: Annotated[Session, Depends(get_session)]):
    # Check if Twilio client is configured
    if not twilio_client or not TWILIO_WHATSAPP_NUMBER:
        print("ERROR: Twilio is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP service is not configured correctly."
        )

    otp = random.randint(100000, 999999)
    phone_number_e164 = payload.whatsapp_number
    
    # Store the OTP
    otp_storage[phone_number_e164] = otp
    print(f"Generated OTP for {phone_number_e164}: {otp}") # For debugging

    try:
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=f"Your StellarHub verification code is: {otp}",
            to=f"whatsapp:{phone_number_e164}"
        )
        return {"message": "OTP sent successfully."}
    except TwilioRestException as e:
        # Handle specific Twilio errors, like an unverified number
        print(f"Twilio Error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to send OTP. Please ensure the number is correct and verified with the Twilio sandbox.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP due to a server error.")

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
    
    # Use a try-except block to handle potential type errors with the OTP
    try:
        is_valid = (stored_otp is not None and stored_otp == int(payload.otp))
    except (ValueError, TypeError):
        is_valid = False

    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")
    
    # Mark user as verified
    user.whatsapp_verified = True
    db.add(user)
    db.commit()
    
    # Clean up OTP
    del otp_storage[user.whatsapp_number]
    
    return {"message": "WhatsApp number verified successfully."}
