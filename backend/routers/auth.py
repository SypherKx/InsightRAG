"""
Authentication & User Access Audit Router.

Tracks logins, access logs, and user identity via Firebase.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from ..storage.database import get_session, UserAccessLogRecord
from ..utils.firebase_auth import (
    get_current_user_optional,
    get_current_user_required,
    require_admin,
    sanitize_input,
)
from ..utils.rate_limiter import rate_limit_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication & Audit"])


class RecordLoginPayload(BaseModel):
    uid: str
    email: Optional[str] = None
    name: Optional[str] = None
    photo_url: Optional[str] = None


class TrackActionPayload(BaseModel):
    action: str
    path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/record-login", dependencies=[Depends(rate_limit_auth)])
async def record_user_login(
    payload: RecordLoginPayload,
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """Record a user sign-in event into the audit database."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = sanitize_input(request.headers.get("user-agent", "unknown"), max_len=200)

    # Use verified user info if token was valid, fallback to sanitized payload
    uid = current_user.get("uid") if current_user else sanitize_input(payload.uid, max_len=128)
    email = current_user.get("email") if current_user else sanitize_input(payload.email, max_len=255)
    name = current_user.get("name") if current_user else sanitize_input(payload.name, max_len=100)

    db: Session = get_session()
    try:
        log_entry = UserAccessLogRecord(
            user_id=uid,
            email=email,
            name=name,
            action="login",
            path="/auth/login",
            ip_address=client_ip,
            user_agent=user_agent,
            meta_info={"photo_url": payload.photo_url},
            created_at=datetime.utcnow(),
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"Recorded login audit for user: {email} ({uid}) from {client_ip}")
        return {"status": "success", "message": "Login recorded successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record login audit: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.post("/track-action", dependencies=[Depends(rate_limit_auth)])
async def track_user_action(
    payload: TrackActionPayload,
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """Track any user activity with rate limiting and sanitization."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = sanitize_input(request.headers.get("user-agent", "unknown"), max_len=200)

    uid = current_user.get("uid") if current_user else None
    email = current_user.get("email") if current_user else None
    name = current_user.get("name") if current_user else None

    clean_action = sanitize_input(payload.action, max_len=50) or "action"
    clean_path = sanitize_input(payload.path or request.url.path, max_len=200)

    db: Session = get_session()
    try:
        log_entry = UserAccessLogRecord(
            user_id=uid,
            email=email,
            name=name,
            action=clean_action,
            path=clean_path,
            ip_address=client_ip,
            user_agent=user_agent,
            meta_info=payload.metadata or {},
            created_at=datetime.utcnow(),
        )
        db.add(log_entry)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record action: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.get("/me")
async def get_me(user: Dict[str, Any] = Depends(get_current_user_required)):
    """Return the profile of the verified authenticated user."""
    return {
        "status": "authenticated",
        "user": user,
    }


@router.get("/logs")
async def get_access_logs(
    limit: int = 50,
    admin: Dict[str, Any] = Depends(require_admin),
):
    """
    Get audit access logs. STRICTLY PROTECTED: Admin privileges required.
    Prevents unauthorized visitors from seeing user emails and IPs.
    """
    db: Session = get_session()
    try:
        logs = (
            db.query(UserAccessLogRecord)
            .order_by(desc(UserAccessLogRecord.created_at))
            .limit(min(limit, 200))
            .all()
        )

        total_entries = db.query(func.count(UserAccessLogRecord.id)).scalar() or 0
        unique_users_count = (
            db.query(func.count(func.distinct(UserAccessLogRecord.email)))
            .filter(UserAccessLogRecord.email.isnot(None))
            .scalar()
            or 0
        )

        return {
            "total_events": total_entries,
            "unique_users_count": unique_users_count,
            "recent_logs": [
                {
                    "id": l.id,
                    "user_id": l.user_id,
                    "email": l.email,
                    "name": l.name,
                    "action": l.action,
                    "path": l.path,
                    "ip_address": l.ip_address,
                    "user_agent": l.user_agent,
                    "timestamp": l.created_at.isoformat() if l.created_at else None,
                }
                for l in logs
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching access logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

