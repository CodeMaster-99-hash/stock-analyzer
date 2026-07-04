"""
models/user.py
==============
Represents an application user.

SECURITY NOTE:
    We never store plain-text passwords anywhere — not in this
    object, not in the database, not in logs.
    Only password_hash is stored. The hashing happens in the
    AuthService (Phase 5, Step 6).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Represents a user account."""

    username:      str
    email:         str
    id:            Optional[int]      = None
    password_hash: Optional[str]      = None
    is_active:     bool               = True
    created_at:    Optional[datetime] = None

    def __post_init__(self):
        self.email    = self.email.lower().strip()
        self.username = self.username.strip()

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(
            id            = data.get('id'),
            username      = data.get('username', ''),
            email         = data.get('email', ''),
            password_hash = data.get('password_hash'),
            is_active     = bool(data.get('is_active', True)),
            created_at    = data.get('created_at'),
        )

    def to_dict(self) -> dict:
        return {
            'id':       self.id,
            'username': self.username,
            'email':    self.email,
        }

    def __str__(self) -> str:
        return f"{self.username} ({self.email})"
