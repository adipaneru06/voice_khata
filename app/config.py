import os
from dotenv import load_dotenv

load_dotenv(override=True)

GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
MOCK_GNANI: bool = os.getenv("MOCK_GNANI", "0") == "1"
SHOP_NAME: str = os.getenv("SHOP_NAME", "My Shop")

# Security & Authentication
SECRET_KEY: str = os.getenv("SECRET_KEY", "khata-voice-production-secret-key-32-bytes-2026")
SESSION_COOKIE_NAME: str = "khata_session"
SESSION_DURATION_DAYS: int = 7
REMEMBER_ME_DURATION_DAYS: int = 30

# Google Maps Platform
GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", os.getenv("VITE_GOOGLE_MAPS_API_KEY", ""))

# Admin Bootstrap
ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@voicekhata.com")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin@123456")

# OTP Delivery Configuration (Mock/Console mode if real SMS/SMTP not configured)
MOCK_OTP: bool = os.getenv("MOCK_OTP", "1") == "1"
OTP_EXPIRY_MINUTES: int = 5
OTP_RESEND_COOLDOWN_SECONDS: int = 45
MAX_OTP_ATTEMPTS: int = 5


