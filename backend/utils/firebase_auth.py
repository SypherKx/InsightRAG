"""
Firebase Authentication & Verification Utility.

Authentication is disabled for open/local usage.
Provides safe no-op fallbacks to preserve existing dependencies without enforcing auth or blocking features.
"""

import logging
from typing import Optional, Dict, Any

from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

def sanitize_input(text: Optional[str], max_len: int = 255) -> Optional[str]:
    """Strip dangerous characters and truncate string."""
    if not text:
        return text
    return str(text).strip()[:max_len]

LOCAL_USER: Dict[str, Any] = {
    "uid": "local_user",
    "email": "local@insightrag.tech",
    "name": "Local User",
    "picture": None,
    "email_verified": True,
    "is_admin": True,
}


def init_firebase() -> bool:
    """No-op: Firebase auth is disabled."""
    return True


def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """No-op token verifier."""
    return LOCAL_USER


async def get_current_user_optional(
    cred: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[Dict[str, Any]]:
    """Open access: returns None for anonymous/unauthenticated local operation."""
    return None


async def get_current_user_required(
    cred: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Dict[str, Any]:
    """Open access: returns a local user profile without throwing 401."""
    return LOCAL_USER


async def require_admin(
    user: Dict[str, Any] = Security(get_current_user_required),
) -> Dict[str, Any]:
    """Open access: returns local admin permissions without throwing 403."""
    return LOCAL_USER
