# In app/core/cloudinary_utils.py

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status, UploadFile
from app.core.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

# Configure Cloudinary
cloudinary.config(
  cloud_name = CLOUDINARY_CLOUD_NAME,
  api_key = CLOUDINARY_API_KEY,
  api_secret = CLOUDINARY_API_SECRET,
  secure = True
)

def upload_to_cloudinary(file: UploadFile, folder: str) -> dict:
    """
    Uploads a file to a specified folder in Cloudinary.
    Returns the upload result dictionary from Cloudinary.
    """
    try:
        # The upload method returns a dictionary with upload details
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            resource_type="image"
        )
        return upload_result
    except Exception as e:
        # Handle potential errors during upload
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image to Cloudinary: {str(e)}"
        )