"""Authentication & OTP Router for Voice Khata."""

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    MOCK_OTP,
    REMEMBER_ME_DURATION_DAYS,
    SESSION_COOKIE_NAME,
    SESSION_DURATION_DAYS,
)
from app.db import Shop, ShopOwner, get_session
from app.security import (
    create_and_send_otp,
    create_session,
    get_owner_from_token,
    hash_password,
    invalidate_all_owner_sessions,
    invalidate_session,
    log_activity,
    normalize_email,
    normalize_phone,
    validate_email_format,
    validate_password_strength,
    validate_phone_format,
    verify_otp_submission,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["Authentication & OTP"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    mobile_number: str
    password: str
    confirm_password: str
    terms_accepted: bool


class LoginRequest(BaseModel):
    identifier: str  # email or phone
    password: str
    remember_me: bool = False


class ForgotPasswordRequest(BaseModel):
    identifier: str
    otp_type: str = "email"  # email | phone


class ResetPasswordRequest(BaseModel):
    identifier: str
    otp_code: str
    otp_type: str = "email"
    new_password: str
    confirm_password: str


class SendOtpRequest(BaseModel):
    target: Optional[str] = None
    otp_type: str = "email"  # email | phone


class VerifyOtpRequest(BaseModel):
    target: Optional[str] = None
    otp_code: str
    otp_type: str = "email"


# ---------------------------------------------------------------------------
# Dependency Helpers
# ---------------------------------------------------------------------------

def extract_token_from_request(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    khata_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    x_session_token: Optional[str] = Header(default=None),
) -> Optional[str]:
    """Extract session token from Bearer auth header, cookie, or custom header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:].strip()
    if x_session_token:
        return x_session_token.strip()
    if khata_session:
        return khata_session.strip()
    return None


def get_current_owner(
    request: Request,
    session: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
    khata_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    x_session_token: Optional[str] = Header(default=None),
) -> ShopOwner:
    """Dependency enforcing that the caller is an authenticated ShopOwner."""
    token = extract_token_from_request(request, authorization, khata_session, x_session_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    owner = get_owner_from_token(session, token)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again.",
        )

    if owner.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {owner.account_status}. Please contact support.",
        )

    return owner


def get_optional_owner(
    request: Request,
    session: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
    khata_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    x_session_token: Optional[str] = Header(default=None),
) -> Optional[ShopOwner]:
    """Optional authentication: returns ShopOwner if valid token provided, else None."""
    token = extract_token_from_request(request, authorization, khata_session, x_session_token)
    if not token:
        return None
    return get_owner_from_token(session, token)


def get_current_admin(
    current_owner: ShopOwner = Depends(get_current_owner),
) -> ShopOwner:
    """Enforce that current user possesses administrator role."""
    if current_owner.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required.",
        )
    return current_owner


# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/register")
def register(
    payload: RegisterRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    """Register a new shop owner account."""
    if not payload.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept the Terms and Conditions to register.",
        )

    full_name = payload.full_name.strip()
    if len(full_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be at least 2 characters.",
        )

    clean_email = normalize_email(payload.email)
    if not validate_email_format(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )

    clean_phone = normalize_phone(payload.mobile_number)
    if not validate_phone_format(clean_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mobile phone format. Please include country code (e.g. +91 9876543210).",
        )

    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    is_strong, pass_msg = validate_password_strength(payload.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pass_msg,
        )

    # Check duplicate email
    existing_email = session.exec(
        select(ShopOwner).where(ShopOwner.email == clean_email)
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please log in or use forgot password.",
        )

    # Check duplicate phone
    existing_phone = session.exec(
        select(ShopOwner).where(ShopOwner.mobile_number == clean_phone)
    ).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this mobile number already exists. Please log in or use forgot password.",
        )

    # Hash password & create owner
    hashed = hash_password(payload.password)
    new_owner = ShopOwner(
        full_name=full_name,
        email=clean_email,
        mobile_number=clean_phone,
        password_hash=hashed,
        email_verified=False,
        phone_verified=False,
        account_status="active",
        role="owner",
    )
    session.add(new_owner)
    session.commit()
    session.refresh(new_owner)

    # Initialize empty shop record in progress
    shop = Shop(
        owner_id=new_owner.id,  # type: ignore[arg-type]
        shop_name=f"{full_name}'s Shop",
        shop_mobile_number=clean_phone,
        shop_email=clean_email,
        is_registration_complete=False,
        registration_step=1,
    )
    session.add(shop)
    session.commit()

    # Automatically send initial email OTP
    otp_code, _ = create_and_send_otp(session, clean_email, "email", new_owner.id)

    log_activity(
        session,
        identifier=clean_email,
        action="registered",
        owner_id=new_owner.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    resp_data = {
        "status": "success",
        "message": "Account registered successfully. Please verify your email or phone.",
        "owner_id": new_owner.id,
        "email": new_owner.email,
        "mobile_number": new_owner.mobile_number,
        "next_step": "verify_otp",
    }
    if MOCK_OTP and otp_code:
        resp_data["dev_otp"] = otp_code

    return resp_data


@router.post("/auth/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    """Authenticate shop owner by email or mobile number."""
    raw_id = payload.identifier.strip()
    if not raw_id or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier and password are required.",
        )

    # Check if identifier is email or phone
    clean_email = normalize_email(raw_id)
    clean_phone = normalize_phone(raw_id)

    owner = session.exec(
        select(ShopOwner).where(
            (ShopOwner.email == clean_email) | (ShopOwner.mobile_number == clean_phone)
        )
    ).first()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if not owner or not verify_password(payload.password, owner.password_hash):
        log_activity(session, identifier=raw_id, action="login_failed", ip_address=ip, user_agent=ua)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your email/mobile and password.",
        )

    if owner.account_status != "active":
        log_activity(
            session,
            identifier=raw_id,
            action="login_blocked",
            owner_id=owner.id,
            ip_address=ip,
            user_agent=ua,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This account has been {owner.account_status}. Please contact administration.",
        )

    # Create active session
    new_session = create_session(
        session,
        owner_id=owner.id,  # type: ignore[arg-type]
        ip_address=ip,
        user_agent=ua,
        remember_me=payload.remember_me,
    )

    # Set secure cookie
    max_age = (
        REMEMBER_ME_DURATION_DAYS * 86400
        if payload.remember_me
        else SESSION_DURATION_DAYS * 86400
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=new_session.token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in HTTPS production
    )

    # Fetch shop
    shop = session.exec(select(Shop).where(Shop.owner_id == owner.id)).first()

    log_activity(
        session,
        identifier=raw_id,
        action="login_success",
        owner_id=owner.id,
        ip_address=ip,
        user_agent=ua,
    )

    return {
        "status": "success",
        "message": "Logged in successfully.",
        "token": new_session.token,
        "owner": {
            "id": owner.id,
            "full_name": owner.full_name,
            "email": owner.email,
            "mobile_number": owner.mobile_number,
            "email_verified": owner.email_verified,
            "phone_verified": owner.phone_verified,
            "role": owner.role,
        },
        "shop": {
            "id": shop.id if shop else None,
            "shop_name": shop.shop_name if shop else "My Shop",
            "is_registration_complete": shop.is_registration_complete if shop else False,
            "registration_step": shop.registration_step if shop else 1,
            "verification_status": shop.verification_status if shop else "pending",
        } if shop else None,
        "is_registration_complete": shop.is_registration_complete if shop else False,
        "registration_step": shop.registration_step if shop else 1,
    }


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
    khata_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    x_session_token: Optional[str] = Header(default=None),
):
    """Log out current session and invalidate token."""
    token = extract_token_from_request(request, authorization, khata_session, x_session_token)
    if token:
        invalidate_session(session, token)

    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {"status": "success", "message": "Logged out successfully."}


@router.post("/auth/logout-all")
def logout_all(
    response: Response,
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Log out from all devices."""
    count = invalidate_all_owner_sessions(session, current_owner.id)  # type: ignore[arg-type]
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {
        "status": "success",
        "message": f"Successfully logged out from {count} device session(s).",
    }


@router.get("/auth/me")
def get_current_user_profile(
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Retrieve currently authenticated owner and active shop profile."""
    shop = session.exec(select(Shop).where(Shop.owner_id == current_owner.id)).first()
    return {
        "owner": {
            "id": current_owner.id,
            "full_name": current_owner.full_name,
            "email": current_owner.email,
            "mobile_number": current_owner.mobile_number,
            "email_verified": current_owner.email_verified,
            "phone_verified": current_owner.phone_verified,
            "account_status": current_owner.account_status,
            "role": current_owner.role,
            "created_at": current_owner.created_at.isoformat(),
        },
        "shop": {
            "id": shop.id if shop else None,
            "shop_name": shop.shop_name if shop else "My Shop",
            "shop_category": shop.shop_category if shop else "",
            "shop_description": shop.shop_description if shop else "",
            "shop_mobile_number": shop.shop_mobile_number if shop else "",
            "opening_time": shop.opening_time if shop else "09:00 AM",
            "closing_time": shop.closing_time if shop else "09:00 PM",
            "complete_address": shop.complete_address if shop else "",
            "city": shop.city if shop else "",
            "state": shop.state if shop else "",
            "pincode": shop.pincode if shop else "",
            "latitude": shop.latitude if shop else None,
            "longitude": shop.longitude if shop else None,
            "google_maps_url": shop.google_maps_url if shop else None,
            "is_registration_complete": shop.is_registration_complete if shop else False,
            "registration_step": shop.registration_step if shop else 1,
            "verification_status": shop.verification_status if shop else "pending",
        } if shop else None,
        "is_registration_complete": shop.is_registration_complete if shop else False,
    }


@router.post("/auth/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    session: Session = Depends(get_session),
):
    """Send a password reset OTP to registered email or mobile number."""
    raw_id = payload.identifier.strip()
    if not raw_id:
        raise HTTPException(status_code=400, detail="Identifier is required.")

    clean_email = normalize_email(raw_id)
    clean_phone = normalize_phone(raw_id)

    owner = session.exec(
        select(ShopOwner).where(
            (ShopOwner.email == clean_email) | (ShopOwner.mobile_number == clean_phone)
        )
    ).first()

    if not owner:
        # Standard generic response prevents user enumeration
        return {
            "status": "success",
            "message": "If an account exists with this credential, a verification code has been sent.",
        }

    target = owner.email if payload.otp_type == "email" else owner.mobile_number
    otp_code, err = create_and_send_otp(session, target, payload.otp_type, owner.id, ignore_cooldown=True)
    if err:
        raise HTTPException(status_code=429, detail=err)

    resp = {
        "status": "success",
        "message": f"Verification code sent to {target}.",
        "target": target,
        "otp_type": payload.otp_type,
    }
    if MOCK_OTP and otp_code:
        resp["dev_otp"] = otp_code
    return resp


@router.post("/auth/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    """Reset account password using verified OTP."""
    raw_id = payload.identifier.strip()
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    is_strong, msg = validate_password_strength(payload.new_password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=msg)

    clean_email = normalize_email(raw_id)
    clean_phone = normalize_phone(raw_id)

    owner = session.exec(
        select(ShopOwner).where(
            (ShopOwner.email == clean_email) | (ShopOwner.mobile_number == clean_phone)
        )
    ).first()

    if not owner:
        raise HTTPException(status_code=404, detail="Account not found.")

    target = owner.email if payload.otp_type == "email" else owner.mobile_number
    is_valid, verify_msg = verify_otp_submission(
        session, target, payload.otp_code, payload.otp_type
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=verify_msg)

    # Update password and invalidate all previous sessions
    owner.password_hash = hash_password(payload.new_password)
    session.add(owner)
    invalidate_all_owner_sessions(session, owner.id)  # type: ignore[arg-type]
    session.commit()

    log_activity(
        session,
        identifier=raw_id,
        action="password_reset",
        owner_id=owner.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "status": "success",
        "message": "Password reset successfully. You can now log in with your new password.",
    }


# ---------------------------------------------------------------------------
# OTP Verification Endpoints
# ---------------------------------------------------------------------------

@router.post("/otp/send-email")
def send_email_otp(
    payload: Optional[SendOtpRequest] = None,
    session: Session = Depends(get_session),
    current_owner: Optional[ShopOwner] = Depends(get_optional_owner),
):
    """Generate and dispatch an email OTP."""
    target = (payload.target if payload and payload.target else None) or (current_owner.email if current_owner else None)
    if not target:
        raise HTTPException(status_code=400, detail="Target email is required.")
    email = normalize_email(target)
    if not validate_email_format(email):
        raise HTTPException(status_code=400, detail="Invalid email format.")

    owner = session.exec(select(ShopOwner).where(ShopOwner.email == email)).first()
    otp_code, err = create_and_send_otp(session, email, "email", owner.id if owner else None)
    if err:
        raise HTTPException(status_code=429, detail=err)

    resp = {
        "status": "success",
        "message": f"Verification code sent to {email}.",
        "target": email,
    }
    if MOCK_OTP and otp_code:
        resp["dev_otp"] = otp_code
    return resp


@router.post("/otp/verify-email")
def verify_email_otp(
    payload: VerifyOtpRequest,
    session: Session = Depends(get_session),
    current_owner: Optional[ShopOwner] = Depends(get_optional_owner),
):
    """Verify an email OTP and mark account as email_verified."""
    target = payload.target or (current_owner.email if current_owner else None)
    if not target:
        raise HTTPException(status_code=400, detail="Target email is required.")
    email = normalize_email(target)
    is_valid, msg = verify_otp_submission(session, email, payload.otp_code, "email")
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    owner = session.exec(select(ShopOwner).where(ShopOwner.email == email)).first()
    if owner:
        owner.email_verified = True
        session.add(owner)
        session.commit()

    return {
        "status": "success",
        "message": "Email verified successfully.",
        "email_verified": True,
    }


@router.post("/otp/send-phone")
def send_phone_otp(
    payload: Optional[SendOtpRequest] = None,
    session: Session = Depends(get_session),
    current_owner: Optional[ShopOwner] = Depends(get_optional_owner),
):
    """Generate and dispatch a phone OTP."""
    target = (payload.target if payload and payload.target else None) or (current_owner.mobile_number if current_owner else None)
    if not target:
        raise HTTPException(status_code=400, detail="Target phone is required.")
    phone = normalize_phone(target)
    if not validate_phone_format(phone):
        raise HTTPException(status_code=400, detail="Invalid phone format.")

    owner = session.exec(select(ShopOwner).where(ShopOwner.mobile_number == phone)).first()
    otp_code, err = create_and_send_otp(session, phone, "phone", owner.id if owner else None)
    if err:
        raise HTTPException(status_code=429, detail=err)

    resp = {
        "status": "success",
        "message": f"Verification code sent to {phone}.",
        "target": phone,
    }
    if MOCK_OTP and otp_code:
        resp["dev_otp"] = otp_code
    return resp


@router.post("/otp/verify-phone")
def verify_phone_otp(
    payload: VerifyOtpRequest,
    session: Session = Depends(get_session),
    current_owner: Optional[ShopOwner] = Depends(get_optional_owner),
):
    """Verify a phone OTP and mark account as phone_verified."""
    target = payload.target or (current_owner.mobile_number if current_owner else None)
    if not target:
        raise HTTPException(status_code=400, detail="Target phone is required.")
    phone = normalize_phone(target)
    is_valid, msg = verify_otp_submission(session, phone, payload.otp_code, "phone")
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    owner = session.exec(select(ShopOwner).where(ShopOwner.mobile_number == phone)).first()
    if owner:
        owner.phone_verified = True
        session.add(owner)
        session.commit()

    return {
        "status": "success",
        "message": "Mobile number verified successfully.",
        "phone_verified": True,
    }
