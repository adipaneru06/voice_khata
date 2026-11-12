"""Admin Management Router for Voice Khata."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.auth_router import get_current_admin
from app.config import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    SESSION_COOKIE_NAME,
    SESSION_DURATION_DAYS,
)
from app.db import Customer, Entry, LoginActivity, Shop, ShopOwner, get_session
from app.security import (
    create_session,
    hash_password,
    invalidate_all_owner_sessions,
    log_activity,
    normalize_email,
    verify_password,
)

router = APIRouter(prefix="/api/admin", tags=["Admin Portal"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AdminLoginRequest(BaseModel):
    email: str
    password: str


class UpdateOwnerStatusRequest(BaseModel):
    account_status: str  # active | suspended | deactivated


class UpdateShopStatusRequest(BaseModel):
    verification_status: str  # verified | pending | rejected


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login")
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    """Authenticate administrator credentials and return admin session token."""
    clean_email = normalize_email(payload.email)

    admin_owner = session.exec(
        select(ShopOwner)
        .where(ShopOwner.email == clean_email)
        .where(ShopOwner.role == "admin")
    ).first()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if not admin_owner or not verify_password(payload.password, admin_owner.password_hash):
        log_activity(session, identifier=clean_email, action="admin_login_failed", ip_address=ip, user_agent=ua)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials.",
        )

    new_session = create_session(
        session,
        owner_id=admin_owner.id,  # type: ignore[arg-type]
        ip_address=ip,
        user_agent=ua,
        remember_me=True,
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=new_session.token,
        max_age=SESSION_DURATION_DAYS * 86400,
        httponly=True,
        samesite="lax",
    )

    log_activity(session, identifier=clean_email, action="admin_login_success", owner_id=admin_owner.id, ip_address=ip, user_agent=ua)

    return {
        "status": "success",
        "message": "Admin login successful.",
        "token": new_session.token,
        "admin": {
            "id": admin_owner.id,
            "full_name": admin_owner.full_name,
            "email": admin_owner.email,
            "role": admin_owner.role,
        },
    }


@router.get("/stats")
def get_admin_dashboard_stats(
    current_admin: ShopOwner = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """Retrieve system-wide aggregated metrics for the admin dashboard."""
    total_owners = session.exec(select(func.count(ShopOwner.id)).where(ShopOwner.role == "owner")).one() or 0
    total_shops = session.exec(select(func.count(Shop.id))).one() or 0
    active_shops = session.exec(
        select(func.count(Shop.id)).where(Shop.verification_status == "verified")
    ).one() or 0
    pending_shops = session.exec(
        select(func.count(Shop.id)).where(Shop.verification_status == "pending")
    ).one() or 0
    total_entries = session.exec(select(func.count(Entry.id))).one() or 0
    total_customers = session.exec(select(func.count(Customer.id))).one() or 0

    return {
        "total_shop_owners": total_owners,
        "total_shops": total_shops,
        "active_verified_shops": active_shops,
        "pending_shops": pending_shops,
        "total_entries": total_entries,
        "total_customers": total_customers,
    }


@router.get("/shop-owners")
def list_all_shop_owners(
    q: Optional[str] = Query(default=None, description="Search term for name, shop name, email, or mobile"),
    city: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    current_admin: ShopOwner = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """List and search all registered shop owners with their shops."""
    query = select(ShopOwner).where(ShopOwner.role == "owner").order_by(ShopOwner.created_at.desc())  # type: ignore[union-attr]
    if status_filter:
        query = query.where(ShopOwner.account_status == status_filter)

    owners = session.exec(query).all()
    results = []

    search_term = q.strip().lower() if q else ""

    for owner in owners:
        shop = session.exec(select(Shop).where(Shop.owner_id == owner.id)).first()

        # Filtering by city or category if provided
        if city and shop and shop.city.strip().lower() != city.strip().lower():
            continue
        if category and shop and shop.shop_category.strip().lower() != category.strip().lower():
            continue

        # Search matching
        if search_term:
            match_owner = (
                search_term in owner.full_name.lower()
                or search_term in owner.email.lower()
                or search_term in owner.mobile_number.lower()
            )
            match_shop = (
                shop
                and (
                    search_term in shop.shop_name.lower()
                    or search_term in shop.city.lower()
                    or (shop.shop_category and search_term in shop.shop_category.lower())
                )
            )
            if not (match_owner or match_shop):
                continue

        results.append({
            "id": owner.id,
            "full_name": owner.full_name,
            "email": owner.email,
            "mobile_number": owner.mobile_number,
            "email_verified": owner.email_verified,
            "phone_verified": owner.phone_verified,
            "account_status": owner.account_status,
            "created_at": owner.created_at.isoformat(),
            "shop": {
                "id": shop.id if shop else None,
                "shop_name": shop.shop_name if shop else "No shop registered",
                "shop_category": shop.shop_category if shop else "N/A",
                "city": shop.city if shop else "N/A",
                "state": shop.state if shop else "N/A",
                "complete_address": shop.complete_address if shop else "N/A",
                "latitude": shop.latitude if shop else None,
                "longitude": shop.longitude if shop else None,
                "google_maps_url": shop.google_maps_url if shop else None,
                "verification_status": shop.verification_status if shop else "pending",
                "is_registration_complete": shop.is_registration_complete if shop else False,
            } if shop else None,
        })

    return results


@router.get("/shops")
def list_all_shops(
    current_admin: ShopOwner = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """List all registered shops with addresses and Google Maps links."""
    shops = session.exec(select(Shop).order_by(Shop.created_at.desc())).all()  # type: ignore[union-attr]
    results = []
    for s in shops:
        owner = session.get(ShopOwner, s.owner_id)
        results.append({
            "id": s.id,
            "owner_id": s.owner_id,
            "owner_name": owner.full_name if owner else "Unknown Owner",
            "owner_email": owner.email if owner else "N/A",
            "owner_mobile": owner.mobile_number if owner else "N/A",
            "shop_name": s.shop_name,
            "shop_category": s.shop_category,
            "shop_mobile_number": s.shop_mobile_number,
            "opening_time": s.opening_time,
            "closing_time": s.closing_time,
            "weekly_closing_day": s.weekly_closing_day,
            "city": s.city,
            "state": s.state,
            "pincode": s.pincode,
            "complete_address": s.complete_address,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "google_maps_url": s.google_maps_url,
            "verification_status": s.verification_status,
            "is_registration_complete": s.is_registration_complete,
            "created_at": s.created_at.isoformat(),
        })
    return results


@router.put("/shop-owners/{owner_id}/status")
def update_shop_owner_status(
    owner_id: int,
    payload: UpdateOwnerStatusRequest,
    current_admin: ShopOwner = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """Activate, suspend, or deactivate a shop owner account."""
    valid_statuses = {"active", "suspended", "deactivated"}
    if payload.account_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid_statuses}")

    owner = session.get(ShopOwner, owner_id)
    if not owner or owner.role == "admin":
        raise HTTPException(status_code=404, detail="Shop owner not found.")

    owner.account_status = payload.account_status
    owner.updated_at = datetime.now(timezone.utc)
    session.add(owner)

    if payload.account_status in {"suspended", "deactivated"}:
        invalidate_all_owner_sessions(session, owner.id)  # type: ignore[arg-type]

    session.commit()
    return {
        "status": "success",
        "message": f"Owner account status updated to {payload.account_status}.",
        "owner_id": owner.id,
        "new_status": owner.account_status,
    }


@router.put("/shops/{shop_id}/status")
def update_shop_verification_status(
    shop_id: int,
    payload: UpdateShopStatusRequest,
    current_admin: ShopOwner = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """Approve, reject, or set pending on a shop profile."""
    valid_statuses = {"verified", "pending", "rejected"}
    if payload.verification_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid verification status. Choose from: {valid_statuses}")

    shop = session.get(Shop, shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found.")

    shop.verification_status = payload.verification_status
    shop.updated_at = datetime.now(timezone.utc)
    session.add(shop)
    session.commit()

    return {
        "status": "success",
        "message": f"Shop verification status updated to {payload.verification_status}.",
        "shop_id": shop.id,
        "new_status": shop.verification_status,
    }


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 50,
    current_admin: ShopOwner = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """Retrieve recent login and administrative audit logs."""
    logs = session.exec(
        select(LoginActivity)
        .order_by(LoginActivity.created_at.desc())  # type: ignore[union-attr]
        .limit(limit)
    ).all()

    return [
        {
            "id": l.id,
            "owner_id": l.owner_id,
            "identifier": l.identifier,
            "action": l.action,
            "ip_address": l.ip_address,
            "user_agent": l.user_agent,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]

