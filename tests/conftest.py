"""
tests/conftest.py
==================
Shared fixtures for all tests.

WHY conftest.py?
    Pytest automatically discovers this file and makes every
    fixture defined here available to ALL test files, with no
    import needed. This avoids repeating setup code everywhere.
"""

import pytest
from unittest.mock import MagicMock
from models.stock import Stock
from models.transaction import Transaction


@pytest.fixture
def sample_stock() -> Stock:
    """
    Returns a sample Stock object for tests.

    WHY A FIXTURE INSTEAD OF CREATING THIS IN EVERY TEST?
        If the Stock model's required fields ever change,
        you fix it in ONE place instead of fifty test files.
    """
    return Stock(
        id=1,
        symbol='AAPL',
        name='Apple Inc.',
        sector='Technology',
        exchange='NASDAQ',
        currency='USD',
        market_cap=2_950_000_000_000,
        pe_ratio=29.5,
    )


@pytest.fixture
def sample_stock_list() -> list[Stock]:
    """Returns multiple sample stocks for list-based tests."""
    return [
        Stock(id=1, symbol='AAPL', name='Apple Inc.', sector='Technology'),
        Stock(id=2, symbol='MSFT', name='Microsoft Corp.', sector='Technology'),
        Stock(id=3, symbol='JPM',  name='JPMorgan Chase', sector='Financial Services'),
    ]


@pytest.fixture
def sample_transaction() -> Transaction:
    """Returns a sample buy transaction."""
    return Transaction(
        portfolio_id=1,
        stock_id=1,
        type='BUY',
        quantity=10,
        price=189.50,
        fees=1.99,
    )


@pytest.fixture
def mock_stock_repository(sample_stock, sample_stock_list):
    """
    Returns a MOCK StockRepository — not the real one.

    WHY MOCK THE REPOSITORY?
        Tests should NOT hit a real MySQL database. That would
        make tests slow, dependent on DB state, and unable to
        run in CI/CD pipelines without a database server.

        A mock object pretends to be a StockRepository but
        returns whatever fake data we configure — instant,
        predictable, and isolated from the real database.
    """
    mock_repo = MagicMock()
    mock_repo.find_by_symbol.return_value = sample_stock
    mock_repo.find_all.return_value = sample_stock_list
    mock_repo.search.return_value = [sample_stock]
    return mock_repo


@pytest.fixture
def sample_price_dataframe():
    """
    Returns a small synthetic price DataFrame for indicator tests.
    Using KNOWN values lets us verify indicator math by hand.
    """
    import pandas as pd
    import numpy as np

    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    # Simple upward trend with slight noise — predictable for testing
    closes = [100 + i * 0.5 + (i % 3) for i in range(30)]

    df = pd.DataFrame({
        'open':   closes,
        'high':   [c + 1 for c in closes],
        'low':    [c - 1 for c in closes],
        'close':  closes,
        'volume': [1_000_000 + i * 10_000 for i in range(30)],
    }, index=dates)

    return df