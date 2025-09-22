from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Annotated
from sqlmodel import Session
import random
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
from app.core.secure_error_handler import SecureErrorHandler, SecureValidator
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
        SecureErrorHandler.log_error(e, "Twilio client initialization")
else:
    SecureErrorHandler.log_error(Exception("Missing credentials"), "Twilio configuration")


class PhonePayload(BaseModel):
    whatsapp_number: str

class OTPPayload(BaseModel):
    otp: str

@router.post("/send-otp", status_code=status.HTTP_200_OK)
def send_otp(payload: PhonePayload, db: Annotated[Session, Depends(get_session)]):
    # Check if Twilio client is configured
    if not twilio_client or not TWILIO_WHATSAPP_NUMBER:
        SecureErrorHandler.log_error(Exception("Twilio not configured"), "OTP service configuration")
        raise SecureErrorHandler.handle_external_service_error(
            Exception("Service not configured"), "OTP"
        )

    otp = random.randint(100000, 999999)
    phone_number_e164 = payload.whatsapp_number
    
    # Store the OTP
    otp_storage[phone_number_e164] = otp
    # Secure logging - don't expose OTP or full phone number
    sanitized_phone = SecureValidator.sanitize_phone_number(phone_number_e164)
    SecureErrorHandler.log_error(Exception("OTP generated"), f"OTP generation for {sanitized_phone}")

    try:
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=f"Your SAMVAD verification code is: {otp}",
            to=f"whatsapp:{phone_number_e164}"
        )
        return {"message": "OTP sent successfully."}
    except TwilioRestException as e:
        # Handle specific Twilio errors securely
        SecureErrorHandler.log_error(e, f"Twilio OTP send to {sanitized_phone}")
        raise HTTPException(
            status_code=400, 
            detail="Failed to send OTP. Please ensure the number is correct and verified."
        )
    except Exception as e:
        # Handle unexpected errors securely
        SecureErrorHandler.log_error(e, f"OTP send to {sanitized_phone}")
        raise SecureErrorHandler.handle_external_service_error(e, "OTP")

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
