"""Security, Authentication, Cryptography & Session Management for Voice Khata."""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from app.config import (
    MAX_OTP_ATTEMPTS,
    OTP_EXPIRY_MINUTES,
    OTP_RESEND_COOLDOWN_SECONDS,
    REMEMBER_ME_DURATION_DAYS,
    SESSION_DURATION_DAYS,
)
from app.db import LoginActivity, OTPVerification, ShopOwner, ShopSession


# ---------------------------------------------------------------------------
# Password Hashing & Verification (PBKDF2-HMAC-SHA256, 260,000 iterations)
# ---------------------------------------------------------------------------

PBKDF2_ROUNDS = 260_000


def hash_password(password: str) -> str:
    """Hash password using cryptographically secure PBKDF2-HMAC-SHA256 with 32-byte salt."""
    salt = secrets.token_bytes(32)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ROUNDS,
    )
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored PBKDF2-HMAC-SHA256 hash using constant-time comparison."""
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        rounds = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])

        candidate_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            rounds,
        )
        return hmac.compare_digest(candidate_key, expected_key)
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength rules: min 8 chars, letter + number or symbol."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[\d\W_]", password):
        return False, "Password must contain at least one number or special character."
    return True, "Password meets requirements."


# ---------------------------------------------------------------------------
# Phone & Email Normalization & Validation
# ---------------------------------------------------------------------------

def normalize_email(email: str) -> str:
    """Normalize email address to lowercase and strip whitespace."""
    return email.strip().lower()


def validate_email_format(email: str) -> bool:
    """Validate standard email format."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def normalize_phone(phone: str) -> str:
    """Normalize phone number to standard international format (e.g. +91XXXXXXXXXX)."""
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("0"):
        cleaned = cleaned[1:]
    if len(cleaned) == 10:
        return f"+91{cleaned}"
    if cleaned.startswith("91") and len(cleaned) == 12:
        return f"+{cleaned}"
    return f"+{cleaned}"


def validate_phone_format(phone: str) -> bool:
    """Validate mobile phone format (must have valid country code + 7-15 digits)."""
    norm = normalize_phone(phone)
    pattern = r"^\+[1-9]\d{6,14}$"
    return bool(re.match(pattern, norm))


# ---------------------------------------------------------------------------
# Session Token Management
# ---------------------------------------------------------------------------

def create_session(
    session: Session,
    owner_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    remember_me: bool = False,
) -> ShopSession:
    """Create a new authenticated session in database."""
    duration_days = REMEMBER_ME_DURATION_DAYS if remember_me else SESSION_DURATION_DAYS
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)

    device_info = "Web Browser"
    if user_agent:
        if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
            device_info = "Mobile Device"
        elif "Windows" in user_agent:
            device_info = "Windows PC"
        elif "Macintosh" in user_agent:
            device_info = "Mac OS"
        elif "Linux" in user_agent:
            device_info = "Linux System"

    shop_session = ShopSession(
        owner_id=owner_id,
        token=token,
        ip_address=ip_address,
        user_agent=user_agent,
        device_info=device_info,
        is_active=True,
        created_at=now,
        last_activity=now,
        expires_at=now + timedelta(days=duration_days),
    )
    session.add(shop_session)
    session.commit()
    session.refresh(shop_session)
    return shop_session


def get_owner_from_token(session: Session, token: str) -> Optional[ShopOwner]:
    """Retrieve active ShopOwner from token, updating last activity and checking expiry."""
    if not token:
        return None

    now = datetime.now(timezone.utc)
    stmt = (
        select(ShopSession)
        .where(ShopSession.token == token)
        .where(ShopSession.is_active == True)  # noqa: E712
        .where(ShopSession.expires_at > now)
    )
    db_session = session.exec(stmt).first()
    if not db_session:
        return None

    # Update last activity timestamp
    db_session.last_activity = now
    session.add(db_session)

    owner = session.get(ShopOwner, db_session.owner_id)
    if not owner or owner.account_status != "active":
        return None

    session.commit()
    return owner


def invalidate_session(session: Session, token: str) -> bool:
    """Invalidate a specific session token."""
    stmt = select(ShopSession).where(ShopSession.token == token)
    db_session = session.exec(stmt).first()
    if db_session:
        db_session.is_active = False
        session.add(db_session)
        session.commit()
        return True
    return False


def invalidate_all_owner_sessions(session: Session, owner_id: int) -> int:
    """Invalidate all active sessions for a shop owner (Logout From All Devices)."""
    stmt = (
        select(ShopSession)
        .where(ShopSession.owner_id == owner_id)
        .where(ShopSession.is_active == True)  # noqa: E712
    )
    sessions = session.exec(stmt).all()
    count = 0
    for s in sessions:
        s.is_active = False
        session.add(s)
        count += 1
    session.commit()
    return count


# ---------------------------------------------------------------------------
# OTP Verification (Hashed in DB, Rate-limited, Expirable, 5 attempts max)
# ---------------------------------------------------------------------------

def generate_otp_code(length: int = 6) -> str:
    """Generate cryptographically secure 6-digit numeric OTP code."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(otp_code: str) -> str:
    """Hash OTP code with SHA-256 before saving to database."""
    return hashlib.sha256(otp_code.encode("utf-8")).hexdigest()


def create_and_send_otp(
    session: Session,
    target: str,
    otp_type: str,
    owner_id: Optional[int] = None,
    ignore_cooldown: bool = False,
) -> tuple[Optional[str], Optional[str]]:
    """Create a new OTP record.

    Returns:
        (plain_otp, error_message): plain_otp is populated on success; error_message on failure.
    """
    target = target.strip()
    if otp_type == "email":
        target = normalize_email(target)
    elif otp_type == "phone":
        target = normalize_phone(target)

    now = datetime.now(timezone.utc)

    # Check resend cooldown
    if not ignore_cooldown:
        cooldown_threshold = now - timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)
        recent_otp = session.exec(
            select(OTPVerification)
            .where(OTPVerification.target == target)
            .where(OTPVerification.otp_type == otp_type)
            .where(OTPVerification.created_at > cooldown_threshold)
            .order_by(OTPVerification.created_at.desc())  # type: ignore[union-attr]
        ).first()

        if recent_otp:
            remaining_secs = int((recent_otp.created_at + timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS) - now).total_seconds())
            remaining_secs = max(remaining_secs, 1)
            return None, f"Please wait {remaining_secs} seconds before requesting another code."

    # Invalidate previous unused OTPs for this target & type
    old_otps = session.exec(
        select(OTPVerification)
        .where(OTPVerification.target == target)
        .where(OTPVerification.otp_type == otp_type)
        .where(OTPVerification.is_used == False)  # noqa: E712
    ).all()
    for o in old_otps:
        o.is_used = True
        session.add(o)

    code = generate_otp_code(6)
    hashed_code = hash_otp(code)
    expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)

    otp_record = OTPVerification(
        owner_id=owner_id,
        target=target,
        otp_type=otp_type,
        otp_hash=hashed_code,
        expires_at=expires_at,
        attempts=0,
        is_used=False,
        created_at=now,
    )
    session.add(otp_record)
    session.commit()

    return code, None


def verify_otp_submission(
    session: Session,
    target: str,
    otp_code: str,
    otp_type: str,
) -> tuple[bool, str]:
    """Verify submitted OTP code against stored hash with rate limit & expiration check.

    Returns:
        (is_valid, message)
    """
    target = target.strip()
    if otp_type == "email":
        target = normalize_email(target)
    elif otp_type == "phone":
        target = normalize_phone(target)

    clean_code = otp_code.strip()
    now = datetime.now(timezone.utc)

    # Find the latest unused OTP
    otp_record = session.exec(
        select(OTPVerification)
        .where(OTPVerification.target == target)
        .where(OTPVerification.otp_type == otp_type)
        .where(OTPVerification.is_used == False)  # noqa: E712
        .order_by(OTPVerification.created_at.desc())  # type: ignore[union-attr]
    ).first()

    if not otp_record:
        return False, "No active verification code found. Please request a new OTP."

    # Check expiration
    if now > otp_record.expires_at:
        otp_record.is_used = True
        session.add(otp_record)
        session.commit()
        return False, "Verification code has expired. Please request a new code."

    # Check maximum attempts
    if otp_record.attempts >= MAX_OTP_ATTEMPTS:
        otp_record.is_used = True
        session.add(otp_record)
        session.commit()
        return False, "Too many incorrect attempts. Please request a new verification code."

    # Increment attempts count
    otp_record.attempts += 1

    # Check hash match
    submitted_hash = hash_otp(clean_code)
    if not hmac.compare_digest(submitted_hash, otp_record.otp_hash):
        session.add(otp_record)
        session.commit()
        remaining = MAX_OTP_ATTEMPTS - otp_record.attempts
        return False, f"Incorrect verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."

    # Match succeeded!
    otp_record.is_used = True
    session.add(otp_record)
    session.commit()
    return True, "Verification successful."


# ---------------------------------------------------------------------------
# Audit & Login Activity Logger
# ---------------------------------------------------------------------------

def log_activity(
    session: Session,
    identifier: str,
    action: str,
    owner_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Record a security or access event to login_activity table."""
    try:
        activity = LoginActivity(
            owner_id=owner_id,
            identifier=identifier[:150],
            action=action[:50],
            ip_address=ip_address[:60] if ip_address else None,
            user_agent=user_agent[:250] if user_agent else None,
            created_at=datetime.now(timezone.utc),
        )
        session.add(activity)
        session.commit()
    except Exception:
        pass
