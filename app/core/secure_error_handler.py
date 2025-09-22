"""
Secure Error Handler for SAMVAD
Provides secure error handling while maintaining app functionality
"""

import logging
from fastapi import HTTPException, status
from typing import Optional, Any
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureErrorHandler:
    """Centralized secure error handling"""
    
    @staticmethod
    def log_error(error: Exception, context: str, user_id: Optional[int] = None) -> None:
        """Securely log errors for debugging without exposing sensitive data"""
        # Create safe error message for logging
        error_msg = f"Error in {context}"
        if user_id:
            error_msg += f" for user {user_id}"
        error_msg += f": {type(error).__name__}"
        
        # Log the actual error for developers (not exposed to users)
        logger.error(f"{error_msg} - Details: {str(error)}")
    
    @staticmethod
    def handle_file_upload_error(error: Exception, operation: str = "file upload") -> HTTPException:
        """Handle file upload errors securely"""
        SecureErrorHandler.log_error(error, f"{operation} operation")
        
        # Return user-friendly error without exposing internals
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{operation.capitalize()} failed. Please try again with a valid image file."
        )
    
    @staticmethod
    def handle_external_service_error(error: Exception, service_name: str) -> HTTPException:
        """Handle external service errors (Cloudinary, Twilio, etc.)"""
        SecureErrorHandler.log_error(error, f"{service_name} service")
        
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service_name} service is temporarily unavailable. Please try again later."
        )
    
    @staticmethod
    def handle_validation_error(field: str, message: Optional[str] = None) -> HTTPException:
        """Handle validation errors safely"""
        safe_message = message or f"Invalid {field} provided. Please check your input."
        
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=safe_message
        )
    
    @staticmethod
    def handle_authentication_error(message: str = "Authentication failed") -> HTTPException:
        """Handle authentication errors"""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    @staticmethod
    def handle_authorization_error(message: str = "Access denied") -> HTTPException:
        """Handle authorization errors"""
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )
    
    @staticmethod
    def handle_not_found_error(resource: str = "Resource") -> HTTPException:
        """Handle not found errors"""
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found"
        )
    
    @staticmethod
    def handle_generic_error(error: Exception, context: str = "operation") -> HTTPException:
        """Handle generic errors securely"""
        SecureErrorHandler.log_error(error, context)
        
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during {context}. Please try again."
        )

# Utility functions for common validations
class SecureValidator:
    """Secure validation utilities"""
    
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    @staticmethod
    def validate_file_upload(file, max_size: Optional[int] = None) -> None:
        """Validate file upload securely"""
        if not file or not file.filename:
            raise SecureErrorHandler.handle_validation_error("file", "No file provided")
        
        # Check file extension
        file_ext = '.' + file.filename.split('.')[-1].lower()
        if file_ext not in SecureValidator.ALLOWED_IMAGE_EXTENSIONS:
            raise SecureErrorHandler.handle_validation_error(
                "file", "Only JPG, PNG, GIF, and WebP images are allowed"
            )
        
        # Check MIME type if available
        if hasattr(file, 'content_type') and file.content_type:
            if file.content_type not in SecureValidator.ALLOWED_MIME_TYPES:
                raise SecureErrorHandler.handle_validation_error(
                    "file", "Invalid file format"
                )
        
        # Check file size
        max_allowed_size = max_size or SecureValidator.MAX_FILE_SIZE
        if hasattr(file, 'size') and file.size and file.size > max_allowed_size:
            size_mb = max_allowed_size // (1024 * 1024)
            raise SecureErrorHandler.handle_validation_error(
                "file", f"File size must be less than {size_mb}MB"
            )
    
    @staticmethod
    def sanitize_phone_number(phone: str) -> str:
        """Sanitize phone number for logging (hide sensitive parts)"""
        if not phone or len(phone) < 4:
            return "****"
        return phone[:2] + "*" * (len(phone) - 4) + phone[-2:]
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email for logging"""
        if not email or '@' not in email:
            return "****@****.***"
        parts = email.split('@')
        username = parts[0][:2] + "*" * max(0, len(parts[0]) - 2)
        domain = parts[1]
        return f"{username}@{domain}"
