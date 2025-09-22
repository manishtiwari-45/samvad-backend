# Whitelist of emails that automatically become Super Admins
SUPER_ADMIN_EMAILS = {
    # Replace these with your actual email addresses
    "manishtiwari2578@gmail.com",      # Platform owner
    "anuradhatiwari2401@gmail.com",       
    "su-24071@sitare.org",      
    "su-24018@sitare.org",        
}

def is_super_admin_email(email: str) -> bool:
    return email.lower() in {admin_email.lower() for admin_email in SUPER_ADMIN_EMAILS}

def get_whitelisted_emails() -> set:
    return SUPER_ADMIN_EMAILS.copy()

# For debugging/logging purposes
def log_super_admin_attempt(email: str, granted: bool) -> None:
    status = "GRANTED" if granted else "DENIED"
    print(f"[SECURITY] Super Admin access {status} for email: {email}")
