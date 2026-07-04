"""
models/portfolio.py
===================
Represents an investment portfolio.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Portfolio:
    """An investment portfolio belonging to a user."""

    user_id:     int
    name:        str
    id:          Optional[int]      = None
    description: Optional[str]      = None
    currency:    str                = 'USD'
    created_at:  Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        return cls(
            id          = data.get('id'),
            user_id     = data.get('user_id'),
            name        = data.get('name', ''),
            description = data.get('description'),
            currency    = data.get('currency', 'USD'),
            created_at  = data.get('created_at'),
        )

    def to_dict(self) -> dict:
        return {
            'id':          self.id,
            'user_id':     self.user_id,
            'name':        self.name,
            'description': self.description,
            'currency':    self.currency,
        }

    def __str__(self) -> str:
        return f"Portfolio({self.name})"
