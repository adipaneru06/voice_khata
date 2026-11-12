"""Shop Owner & Registration Wizard Router for Voice Khata."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth_router import get_current_owner
from app.db import Shop, ShopOwner, ShopSession, get_session
from app.security import (
    hash_password,
    invalidate_all_owner_sessions,
    log_activity,
    normalize_phone,
    validate_password_strength,
    validate_phone_format,
    verify_password,
)

router = APIRouter(prefix="/api/shop-owner", tags=["Shop Owner & Profile"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class WizardStepRequest(BaseModel):
    step: int
    data: dict


class CompleteWizardRequest(BaseModel):
    shop_name: str
    shop_category: str
    custom_category: Optional[str] = None
    shop_description: Optional[str] = None
    shop_mobile_number: str
    alternative_mobile_number: Optional[str] = None
    alternative_contact_number: Optional[str] = None
    shop_email: Optional[str] = None
    opening_time: str = "09:00 AM"
    closing_time: str = "09:00 PM"
    weekly_closing_day: str = "None"
    house_number: Optional[str] = None
    building_name: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    landmark: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str = "India"
    complete_address: Optional[str] = None
    shop_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None


class UpdateShopRequest(BaseModel):
    shop_name: Optional[str] = None
    shop_category: Optional[str] = None
    custom_category: Optional[str] = None
    shop_description: Optional[str] = None
    shop_mobile_number: Optional[str] = None
    alternative_mobile_number: Optional[str] = None
    alternative_contact_number: Optional[str] = None
    shop_email: Optional[str] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    weekly_closing_day: Optional[str] = None
    house_number: Optional[str] = None
    building_name: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    complete_address: Optional[str] = None
    shop_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    mobile_number: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
def get_owner_status(
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Retrieve owner verification and shop registration progress status."""
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
        },
        "shop": {
            "id": shop.id if shop else None,
            "shop_name": shop.shop_name if shop else None,
            "is_registration_complete": shop.is_registration_complete if shop else False,
            "registration_step": shop.registration_step if shop else 1,
            "verification_status": shop.verification_status if shop else "pending",
        } if shop else None,
        "is_registration_complete": shop.is_registration_complete if shop else False,
        "registration_step": shop.registration_step if shop else 1,
    }


@router.post("/wizard/step")
def save_wizard_step_progress(
    payload: WizardStepRequest,
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Save in-progress registration wizard step to prevent loss of information on reload."""
    shop = session.exec(select(Shop).where(Shop.owner_id == current_owner.id)).first()
    if not shop:
        shop = Shop(owner_id=current_owner.id)  # type: ignore[arg-type]
        session.add(shop)

    shop.registration_step = min(max(payload.step, 1), 4)
    data = payload.data or {}

    # Update available fields from step
    if "shop_name" in data and data["shop_name"]:
        shop.shop_name = data["shop_name"]
    if "shop_category" in data and data["shop_category"]:
        shop.shop_category = data["shop_category"]
    if "custom_category" in data:
        shop.custom_category = data["custom_category"]
    if "shop_description" in data:
        shop.shop_description = data["shop_description"]
    if "shop_mobile_number" in data and data["shop_mobile_number"]:
        shop.shop_mobile_number = data["shop_mobile_number"]
    if "alternative_mobile_number" in data:
        shop.alternative_mobile_number = data["alternative_mobile_number"]
    if "shop_email" in data:
        shop.shop_email = data["shop_email"]
    if "opening_time" in data:
        shop.opening_time = data["opening_time"]
    if "closing_time" in data:
        shop.closing_time = data["closing_time"]
    if "weekly_closing_day" in data:
        shop.weekly_closing_day = data["weekly_closing_day"]

    # Address & Maps Fields
    if "house_number" in data:
        shop.house_number = data["house_number"]
    if "building_name" in data:
        shop.building_name = data["building_name"]
    if "street" in data:
        shop.street = data["street"]
    if "locality" in data:
        shop.locality = data["locality"]
    if "city" in data and data["city"]:
        shop.city = data["city"]
    if "state" in data and data["state"]:
        shop.state = data["state"]
    if "pincode" in data and data["pincode"]:
        shop.pincode = data["pincode"]
    if "country" in data:
        shop.country = data["country"]
    if "complete_address" in data:
        shop.complete_address = data["complete_address"]
    if "latitude" in data and data["latitude"] is not None:
        shop.latitude = float(data["latitude"])
    if "longitude" in data and data["longitude"] is not None:
        shop.longitude = float(data["longitude"])
    if "google_place_id" in data:
        shop.google_place_id = data["google_place_id"]
    if "google_maps_url" in data:
        shop.google_maps_url = data["google_maps_url"]

    shop.updated_at = datetime.now(timezone.utc)
    session.add(shop)
    session.commit()
    session.refresh(shop)

    return {
        "status": "success",
        "message": f"Step {payload.step} progress saved.",
        "registration_step": shop.registration_step,
    }


@router.post("/wizard/complete")
def complete_registration_wizard(
    payload: CompleteWizardRequest,
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Validate all four steps, bind shop profile, and finalize registration."""
    # Validate required fields
    if not payload.shop_name.strip():
        raise HTTPException(status_code=400, detail="Shop name is required.")
    if not payload.shop_category.strip():
        raise HTTPException(status_code=400, detail="Shop category is required.")
    if not payload.shop_mobile_number.strip():
        raise HTTPException(status_code=400, detail="Shop mobile number is required.")
    if not payload.city.strip() or not payload.state.strip() or not payload.pincode.strip():
        raise HTTPException(status_code=400, detail="City, State, and PIN Code are required.")
    address_str = payload.complete_address or payload.shop_address or f"{payload.city}, {payload.state}"
    if not address_str.strip():
        raise HTTPException(status_code=400, detail="Complete shop address is required.")

    shop = session.exec(select(Shop).where(Shop.owner_id == current_owner.id)).first()
    if not shop:
        shop = Shop(owner_id=current_owner.id)  # type: ignore[arg-type]

    # Generate dynamic Google Maps navigation URL if coordinates present
    gmaps_url = payload.google_maps_url
    if not gmaps_url and payload.latitude and payload.longitude:
        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={payload.latitude},{payload.longitude}"

    alt_phone = payload.alternative_mobile_number or payload.alternative_contact_number
    shop.shop_name = payload.shop_name.strip()
    shop.shop_category = payload.shop_category.strip()
    shop.custom_category = payload.custom_category.strip() if payload.custom_category else None
    shop.shop_description = payload.shop_description.strip() if payload.shop_description else None
    shop.shop_mobile_number = payload.shop_mobile_number.strip()
    shop.alternative_mobile_number = alt_phone.strip() if alt_phone else None
    shop.shop_email = payload.shop_email.strip() if payload.shop_email else None
    shop.opening_time = payload.opening_time.strip()
    shop.closing_time = payload.closing_time.strip()
    shop.weekly_closing_day = payload.weekly_closing_day.strip()
    shop.house_number = payload.house_number.strip() if payload.house_number else None
    shop.building_name = payload.building_name.strip() if payload.building_name else None
    shop.street = payload.street.strip() if payload.street else None
    shop.locality = (payload.locality or payload.landmark or "").strip() or None
    shop.city = payload.city.strip()
    shop.state = payload.state.strip()
    shop.pincode = payload.pincode.strip()
    shop.country = payload.country.strip() or "India"
    shop.complete_address = address_str.strip()
    shop.latitude = payload.latitude
    shop.longitude = payload.longitude
    shop.google_place_id = payload.google_place_id
    shop.google_maps_url = gmaps_url
    shop.is_registration_complete = True
    shop.registration_step = 4
    shop.verification_status = "verified"
    shop.updated_at = datetime.now(timezone.utc)

    session.add(shop)
    session.commit()
    session.refresh(shop)

    log_activity(
        session,
        identifier=current_owner.email,
        action="shop_registered",
        owner_id=current_owner.id,
    )

    return {
        "status": "success",
        "message": "Shop registered successfully! Welcome to your Shop Dashboard.",
        "shop": {
            "id": shop.id,
            "shop_name": shop.shop_name,
            "shop_category": shop.shop_category,
            "complete_address": shop.complete_address,
            "city": shop.city,
            "state": shop.state,
            "latitude": shop.latitude,
            "longitude": shop.longitude,
            "google_maps_url": shop.google_maps_url,
            "is_registration_complete": shop.is_registration_complete,
            "verification_status": shop.verification_status,
        },
    }


@router.get("/shop")
def get_shop_details(
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Retrieve authenticated owner's full shop details."""
    shop = session.exec(select(Shop).where(Shop.owner_id == current_owner.id)).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop profile not found.")

    return {
        "id": shop.id,
        "owner_id": shop.owner_id,
        "owner_name": current_owner.full_name,
        "shop_name": shop.shop_name,
        "shop_category": shop.shop_category,
        "custom_category": shop.custom_category,
        "shop_description": shop.shop_description,
        "shop_mobile_number": shop.shop_mobile_number,
        "alternative_mobile_number": shop.alternative_mobile_number,
        "shop_email": shop.shop_email,
        "opening_time": shop.opening_time,
        "closing_time": shop.closing_time,
        "weekly_closing_day": shop.weekly_closing_day,
        "house_number": shop.house_number,
        "building_name": shop.building_name,
        "street": shop.street,
        "locality": shop.locality,
        "city": shop.city,
        "state": shop.state,
        "pincode": shop.pincode,
        "country": shop.country,
        "complete_address": shop.complete_address,
        "latitude": shop.latitude,
        "longitude": shop.longitude,
        "google_place_id": shop.google_place_id,
        "google_maps_url": shop.google_maps_url,
        "is_registration_complete": shop.is_registration_complete,
        "verification_status": shop.verification_status,
        "created_at": shop.created_at.isoformat(),
        "updated_at": shop.updated_at.isoformat(),
    }


@router.put("/shop")
def update_shop_details(
    payload: UpdateShopRequest,
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Update shop information, operating hours, address, or location."""
    shop = session.exec(select(Shop).where(Shop.owner_id == current_owner.id)).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop profile not found.")

    data = payload.model_dump(exclude_unset=True)
    if "shop_address" in data and "complete_address" not in data:
        shop.complete_address = data["shop_address"]
    if "landmark" in data and "locality" not in data:
        shop.locality = data["landmark"]
    for field, val in data.items():
        if val is not None and hasattr(shop, field):
            setattr(shop, field, val)

    # Re-generate google_maps_url if coordinates updated
    if shop.latitude and shop.longitude and not shop.google_maps_url:
        shop.google_maps_url = f"https://www.google.com/maps/search/?api=1&query={shop.latitude},{shop.longitude}"

    shop.updated_at = datetime.now(timezone.utc)
    session.add(shop)
    session.commit()
    session.refresh(shop)

    log_activity(
        session,
        identifier=current_owner.email,
        action="shop_updated",
        owner_id=current_owner.id,
    )

    return {
        "status": "success",
        "message": "Shop details updated successfully.",
        "shop": {
            "id": shop.id,
            "shop_name": shop.shop_name,
            "shop_category": shop.shop_category,
            "complete_address": shop.complete_address,
            "latitude": shop.latitude,
            "longitude": shop.longitude,
            "google_maps_url": shop.google_maps_url,
        },
    }


@router.get("/profile")
def get_owner_profile(
    current_owner: ShopOwner = Depends(get_current_owner),
):
    """Retrieve authenticated owner account profile."""
    return {
        "id": current_owner.id,
        "full_name": current_owner.full_name,
        "email": current_owner.email,
        "mobile_number": current_owner.mobile_number,
        "email_verified": current_owner.email_verified,
        "phone_verified": current_owner.phone_verified,
        "account_status": current_owner.account_status,
        "role": current_owner.role,
        "created_at": current_owner.created_at.isoformat(),
        "last_login": current_owner.last_login.isoformat() if current_owner.last_login else None,
    }


@router.put("/profile")
def update_owner_profile(
    payload: UpdateProfileRequest,
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Update shop owner name or mobile number."""
    if payload.full_name:
        fn = payload.full_name.strip()
        if len(fn) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters.")
        current_owner.full_name = fn

    if payload.mobile_number:
        clean_phone = normalize_phone(payload.mobile_number)
        if not validate_phone_format(clean_phone):
            raise HTTPException(status_code=400, detail="Invalid mobile number format.")
        # Check if already in use by another owner
        existing = session.exec(
            select(ShopOwner)
            .where(ShopOwner.mobile_number == clean_phone)
            .where(ShopOwner.id != current_owner.id)
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Mobile number is already registered to another account.")
        current_owner.mobile_number = clean_phone
        current_owner.phone_verified = False  # requires re-verification

    current_owner.updated_at = datetime.now(timezone.utc)
    session.add(current_owner)
    session.commit()
    session.refresh(current_owner)

    return {
        "status": "success",
        "message": "Profile updated successfully.",
        "owner": {
            "id": current_owner.id,
            "full_name": current_owner.full_name,
            "email": current_owner.email,
            "mobile_number": current_owner.mobile_number,
            "email_verified": current_owner.email_verified,
            "phone_verified": current_owner.phone_verified,
        },
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Change account password validating the current password."""
    if not verify_password(payload.current_password, current_owner.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match.")

    is_strong, msg = validate_password_strength(payload.new_password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=msg)

    current_owner.password_hash = hash_password(payload.new_password)
    current_owner.updated_at = datetime.now(timezone.utc)
    session.add(current_owner)
    session.commit()

    log_activity(
        session,
        identifier=current_owner.email,
        action="password_changed",
        owner_id=current_owner.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return {"status": "success", "message": "Password changed successfully."}


@router.get("/sessions")
def list_active_sessions(
    request: Request,
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """List active login sessions on this account."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(ShopSession)
        .where(ShopSession.owner_id == current_owner.id)
        .where(ShopSession.is_active == True)  # noqa: E712
        .where(ShopSession.expires_at > now)
        .order_by(ShopSession.last_activity.desc())  # type: ignore[union-attr]
    )
    sessions = session.exec(stmt).all()

    auth_header = request.headers.get("authorization", "")
    current_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""

    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "device_info": s.device_info or "Web Browser",
            "ip_address": s.ip_address or "Unknown IP",
            "created_at": s.created_at.isoformat(),
            "last_activity": s.last_activity.isoformat(),
            "is_current": s.token == current_token,
        })
    return result


@router.delete("/sessions/{session_id}")
def terminate_session(
    session_id: int,
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Terminate a specific login session."""
    target_session = session.get(ShopSession, session_id)
    if not target_session or target_session.owner_id != current_owner.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    target_session.is_active = False
    session.add(target_session)
    session.commit()
    return {"status": "success", "message": "Session terminated."}


@router.post("/deactivate")
def deactivate_account(
    current_owner: ShopOwner = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Deactivate shop owner account and invalidate all sessions."""
    current_owner.account_status = "deactivated"
    current_owner.updated_at = datetime.now(timezone.utc)
    session.add(current_owner)
    invalidate_all_owner_sessions(session, current_owner.id)  # type: ignore[arg-type]
    session.commit()

    return {"status": "success", "message": "Account deactivated successfully."}

