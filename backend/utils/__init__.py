"""
InsightRAG Backend Utilities.

Includes:
- firebase_auth: Firebase Admin token validation and admin RBAC
- rate_limiter: Sliding-window in-memory anti-abuse & DoS protection
- security: Path traversal validation and safe file path sanitization
"""

from .security import sanitize_filename, validate_safe_path
from .firebase_auth import (
    verify_firebase_token,
    get_current_user_optional,
    get_current_user_required,
    require_admin,
    sanitize_input,
)
from .rate_limiter import check_rate_limit, rate_limit_auth

__all__ = [
    "sanitize_filename",
    "validate_safe_path",
    "verify_firebase_token",
    "get_current_user_optional",
    "get_current_user_required",
    "require_admin",
    "sanitize_input",
    "check_rate_limit",
    "rate_limit_auth",
]

