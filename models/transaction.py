"""
models/transaction.py
=====================
Represents a single buy or sell transaction in a portfolio.

WHY TRANSACTIONS INSTEAD OF HOLDINGS?
    We never store "I own 10 shares of AAPL."
    We store every individual trade:
        BUY  5 AAPL @ $150
        BUY  5 AAPL @ $160
        SELL 3 AAPL @ $180

    Current holdings = sum of all buys minus sum of all sells.
    This gives us a complete audit trail and lets us calculate
    cost basis, P&L, and performance over any time period.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    """Represents a single buy or sell trade."""

    portfolio_id: int
    stock_id:     int
    type:         str        # 'BUY' or 'SELL'
    quantity:     float
    price:        float
    id:           Optional[int]      = None
    fees:         float              = 0.0
    notes:        Optional[str]      = None
    trans_date:   Optional[datetime] = None
    created_at:   Optional[datetime] = None

    def __post_init__(self):
        self.type = self.type.upper()
        if self.type not in ('BUY', 'SELL'):
            raise ValueError(f"Transaction type must be BUY or SELL, got: {self.type}")
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive, got: {self.quantity}")
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got: {self.price}")

    @property
    def total_value(self) -> float:
        """Total cost of this transaction including fees."""
        return round(self.quantity * self.price + self.fees, 4)

    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        return cls(
            id           = data.get('id'),
            portfolio_id = data.get('portfolio_id'),
            stock_id     = data.get('stock_id'),
            type         = data.get('type', 'BUY'),
            quantity     = float(data.get('quantity', 0)),
            price        = float(data.get('price', 0)),
            fees         = float(data.get('fees', 0)),
            notes        = data.get('notes'),
            trans_date   = data.get('trans_date'),
        )

    def to_dict(self) -> dict:
        return {
            'id':           self.id,
            'portfolio_id': self.portfolio_id,
            'stock_id':     self.stock_id,
            'type':         self.type,
            'quantity':     self.quantity,
            'price':        self.price,
            'fees':         self.fees,
            'notes':        self.notes,
            'trans_date':   str(self.trans_date) if self.trans_date else None,
            'total_value':  self.total_value,
        }
