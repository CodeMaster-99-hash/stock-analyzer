"""
models/stock.py
===============
The Stock model represents a single stock in our application.

WHY MODELS EXIST:
    Without models, data moves around as raw dictionaries:
        {'symbol': 'AAPL', 'name': 'Apple Inc.', ...}

    The problem is you can mistype a key anywhere:
        stock['symboll']  # typo — fails silently or crashes at runtime

    With a model class, your editor autocompletes stock.symbol
    and Python raises an error immediately if the attribute is wrong.
    This is called 'type safety' and it makes debugging much faster.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Stock:
    """
    Represents a stock/company in the system.

    WHY @dataclass?
        Normally a class needs __init__, __repr__, __eq__ written manually.
        @dataclass generates all of these automatically from the field
        definitions below. Less code, same result.
    """

    symbol:         str
    name:           str
    id:             Optional[int]   = None
    sector:         Optional[str]   = None
    industry:       Optional[str]   = None
    exchange:       Optional[str]   = None
    country:        Optional[str]   = None
    currency:       str             = 'USD'
    market_cap:     Optional[float] = None
    pe_ratio:       Optional[float] = None
    dividend_yield: Optional[float] = None
    week_52_high:   Optional[float] = None
    week_52_low:    Optional[float] = None
    description:    Optional[str]   = None
    is_active:      bool            = True
    last_updated:   Optional[datetime] = None

    def __post_init__(self):
        """
        Runs automatically after __init__.
        We use it to clean and validate data as soon as
        a Stock object is created.
        """
        # Always store symbols in uppercase (AAPL not aapl)
        self.symbol = self.symbol.upper().strip()
        self.name   = self.name.strip()

    @property
    def display_name(self) -> str:
        """
        WHY A PROPERTY?
            This value is computed from other fields — it's not stored.
            A property lets us access it like an attribute: stock.display_name
            without calling a method: stock.get_display_name()
        """
        return f"{self.symbol} — {self.name}"

    @property
    def is_us_stock(self) -> bool:
        """Returns True if this stock trades on a US exchange."""
        us_exchanges = {'NYSE', 'NASDAQ', 'AMEX', 'ARCA'}
        return self.exchange in us_exchanges if self.exchange else False

    @classmethod
    def from_dict(cls, data: dict) -> 'Stock':
        """
        Creates a Stock from a dictionary.

        WHY THIS METHOD?
            When we read a row from MySQL, we get back a dict:
                {'id': 1, 'symbol': 'AAPL', 'name': 'Apple Inc.', ...}

            This method converts that dict into a proper Stock object.
            Usage: stock = Stock.from_dict(db_row)
        """
        return cls(
            id             = data.get('id'),
            symbol         = data.get('symbol', ''),
            name           = data.get('name', ''),
            sector         = data.get('sector'),
            industry       = data.get('industry'),
            exchange       = data.get('exchange'),
            country        = data.get('country'),
            currency       = data.get('currency', 'USD'),
            market_cap     = data.get('market_cap'),
            pe_ratio       = data.get('pe_ratio'),
            dividend_yield = data.get('dividend_yield'),
            week_52_high   = data.get('week_52_high'),
            week_52_low    = data.get('week_52_low'),
            description    = data.get('description'),
            is_active      = bool(data.get('is_active', True)),
            last_updated   = data.get('last_updated'),
        )

    def to_dict(self) -> dict:
        """
        Converts this Stock back to a dictionary.
        Useful when saving to the database or sending as JSON.
        """
        return {
            'id':             self.id,
            'symbol':         self.symbol,
            'name':           self.name,
            'sector':         self.sector,
            'industry':       self.industry,
            'exchange':       self.exchange,
            'country':        self.country,
            'currency':       self.currency,
            'market_cap':     self.market_cap,
            'pe_ratio':       self.pe_ratio,
            'dividend_yield': self.dividend_yield,
            'week_52_high':   self.week_52_high,
            'week_52_low':    self.week_52_low,
            'description':    self.description,
            'is_active':      self.is_active,
        }

    def __str__(self) -> str:
        return self.display_name
