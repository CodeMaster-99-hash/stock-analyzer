"""
models/alert.py
===============
Represents a price alert set by a user for a stock.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Alert:
    """A price alert that triggers when a condition is met."""

    user_id:         int
    stock_id:        int
    alert_condition: str    # 'ABOVE', 'BELOW', 'PERCENT_CHANGE'
    id:              Optional[int]      = None
    target_price:    Optional[float]    = None
    percent_value:   Optional[float]    = None
    message:         Optional[str]      = None
    is_active:       bool               = True
    triggered_at:    Optional[datetime] = None
    created_at:      Optional[datetime] = None

    def __post_init__(self):
        valid = {'ABOVE', 'BELOW', 'PERCENT_CHANGE'}
        if self.alert_condition not in valid:
            raise ValueError(f"alert_condition must be one of {valid}")

    @classmethod
    def from_dict(cls, data: dict) -> 'Alert':
        return cls(
            id              = data.get('id'),
            user_id         = data.get('user_id'),
            stock_id        = data.get('stock_id'),
            alert_condition = data.get('alert_condition', 'ABOVE'),
            target_price    = data.get('target_price'),
            percent_value   = data.get('percent_value'),
            message         = data.get('message'),
            is_active       = bool(data.get('is_active', True)),
            triggered_at    = data.get('triggered_at'),
        )

    def to_dict(self) -> dict:
        return {
            'id':              self.id,
            'user_id':         self.user_id,
            'stock_id':        self.stock_id,
            'alert_condition': self.alert_condition,
            'target_price':    self.target_price,
            'percent_value':   self.percent_value,
            'message':         self.message,
            'is_active':       self.is_active,
        }
