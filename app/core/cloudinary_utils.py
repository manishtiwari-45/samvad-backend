# In app/core/cloudinary_utils.py

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status, UploadFile
from app.core.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
from app.core.secure_error_handler import SecureErrorHandler, SecureValidator

# Configure Cloudinary
cloudinary.config(
  cloud_name = CLOUDINARY_CLOUD_NAME,
  api_key = CLOUDINARY_API_KEY,
  api_secret = CLOUDINARY_API_SECRET,
  secure = True
)

def upload_to_cloudinary(file: UploadFile, folder: str) -> dict:
    """
    Securely uploads a file to a specified folder in Cloudinary.
    Returns the upload result dictionary from Cloudinary.
    """
    try:
        # Validate file before upload
        SecureValidator.validate_file_upload(file)
        
        # Upload with security restrictions
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            resource_type="image",
            allowed_formats=["jpg", "jpeg", "png", "gif", "webp"],
            max_file_size=SecureValidator.MAX_FILE_SIZE
        )
        return upload_result
    except HTTPException:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Handle upload errors securely
        raise SecureErrorHandler.handle_external_service_error(e, "Image upload")