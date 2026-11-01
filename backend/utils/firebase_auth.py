"""
Firebase Authentication & Verification Utility.

Verifies Firebase ID Tokens using Firebase Admin SDK.
"""

import os
import re
import html
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException, Security, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings

logger = logging.getLogger(__name__)

# Path to service account key in backend directory
ROOT_DIR = Path(__file__).resolve().parent.parent
SERVICE_KEY_PATH = ROOT_DIR / "serviceAccountKey.json"

_firebase_initialized = False


def init_firebase() -> bool:
    """Initialize Firebase Admin SDK once."""
    global _firebase_initialized
    if _firebase_initialized:
        return True

    try:
        if SERVICE_KEY_PATH.exists():
            cred = credentials.Certificate(str(SERVICE_KEY_PATH))
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin initialized with certificate: {SERVICE_KEY_PATH.name}")
        else:
            # Fallback for serverless or environments with PROJECT_ID
            project_id = os.getenv("FIREBASE_PROJECT_ID", "insightrag-ad79a")
            firebase_admin.initialize_app(options={"projectId": project_id})
            logger.info(f"Firebase Admin initialized with project_id: {project_id}")

        _firebase_initialized = True
        return True
    except ValueError:
        # App might already be initialized
        _firebase_initialized = True
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
        return False


# Auto-initialize on import
init_firebase()

security = HTTPBearer(auto_error=False)


def sanitize_input(text: Optional[str], max_len: int = 255) -> Optional[str]:
    """Strip HTML, script tags, and truncate string to prevent injection."""
    if not text:
        return text
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]*?>", "", str(text))
    # Escape dangerous HTML entities
    cleaned = html.escape(cleaned)
    # Strip null bytes and control chars
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", cleaned)
    return cleaned.strip()[:max_len]


def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """Verify a Firebase ID Token with clock skew tolerance and return claims."""
    if not init_firebase():
        logger.warning("Firebase Admin is not initialized")
        return None

    try:
        decoded_claims = auth.verify_id_token(
            id_token,
            check_revoked=False,
            clock_skew_seconds=10,
        )
        email = decoded_claims.get("email")
        is_admin = bool(email and email.lower() in settings.admin_email_list)
        return {
            "uid": decoded_claims.get("uid"),
            "email": email,
            "name": sanitize_input(decoded_claims.get("name"), max_len=100),
            "picture": decoded_claims.get("picture"),
            "email_verified": decoded_claims.get("email_verified", False),
            "auth_time": decoded_claims.get("auth_time"),
            "is_admin": is_admin,
        }
    except Exception as e:
        logger.warning(f"Invalid Firebase ID token: {e}")
        return None


async def get_current_user_optional(
    cred: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[Dict[str, Any]]:
    """Extract and verify user from Bearer token if present (does not fail if absent)."""
    if not cred or not cred.credentials:
        return None
    return verify_firebase_token(cred.credentials)


async def get_current_user_required(
    cred: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Dict[str, Any]:
    """Require a valid Firebase authenticated user."""
    if not cred or not cred.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid Firebase Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = verify_firebase_token(cred.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Firebase authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(
    user: Dict[str, Any] = Depends(get_current_user_required),
) -> Dict[str, Any]:
    """Require user to be an authorized administrator."""
    if not user.get("is_admin"):
        user_email = user.get("email") or user.get("uid")
        logger.warning(f"Unauthorized admin access attempt by {user_email}")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Administrative privileges required to access this resource.",
        )
    return user

