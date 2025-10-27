# sentry/auth/session.py
"""Simple in-memory session manager used by presenters and tests.

This provides create/validate/invalidate operations. It's intentionally
minimal and intended for development/testing; production would use a
persistent store or JWTs.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

SESSION_TTL_MINUTES = 60


class SessionManager:
    def __init__(self):
        # token -> session data
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, user_id: int, user_data: Dict[str, Any] = None, remember_me: bool = False) -> str:
        token = secrets.token_hex(32)
        ttl = timedelta(days=30) if remember_me else timedelta(minutes=SESSION_TTL_MINUTES)
        self._sessions[token] = {
            "user_id": user_id,
            "user_data": user_data or {},
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + ttl,
        }
        return token

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        data = self._sessions.get(token)
        if not data:
            return None
        if data["expires_at"] < datetime.utcnow():
            # expired
            self._sessions.pop(token, None)
            return None
        return data

    def invalidate_session(self, token: str) -> bool:
        return self._sessions.pop(token, None) is not None
