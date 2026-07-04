"""
tests/test_models.py
=====================
Unit tests for model classes (Stock, Transaction, Alert).
These are pure data classes — fast tests, no mocking needed.
"""

import pytest
from models.stock import Stock
from models.transaction import Transaction
from models.alert import Alert


class TestStockModel:
    """Tests for the Stock dataclass."""

    def test_symbol_is_uppercased(self):
        """Symbols should always be stored uppercase."""
        stock = Stock(symbol='aapl', name='Apple Inc.')
        assert stock.symbol == 'AAPL'

    def test_symbol_whitespace_stripped(self):
        """Leading/trailing whitespace should be removed."""
        stock = Stock(symbol='  AAPL  ', name='Apple Inc.')
        assert stock.symbol == 'AAPL'

    def test_display_name_format(self):
        """display_name should combine symbol and name correctly."""
        stock = Stock(symbol='AAPL', name='Apple Inc.')
        assert stock.display_name == 'AAPL — Apple Inc.'

    def test_is_us_stock_true_for_nasdaq(self):
        stock = Stock(symbol='AAPL', name='Apple', exchange='NASDAQ')
        assert stock.is_us_stock is True

    def test_is_us_stock_false_for_unknown_exchange(self):
        stock = Stock(symbol='SHEL', name='Shell', exchange='LSE')
        assert stock.is_us_stock is False

    def test_is_us_stock_false_when_exchange_none(self):
        stock = Stock(symbol='AAPL', name='Apple')
        assert stock.is_us_stock is False

    def test_from_dict_creates_valid_stock(self):
        """from_dict should correctly map database row to Stock."""
        row = {
            'id': 5, 'symbol': 'tsla', 'name': 'Tesla Inc.',
            'sector': 'Consumer Cyclical', 'is_active': 1,
        }
        stock = Stock.from_dict(row)
        assert stock.id == 5
        assert stock.symbol == 'TSLA'
        assert stock.is_active is True

    def test_to_dict_roundtrip(self, sample_stock):
        """Converting to dict and back should preserve data."""
        d = sample_stock.to_dict()
        rebuilt = Stock.from_dict(d)
        assert rebuilt.symbol == sample_stock.symbol
        assert rebuilt.name   == sample_stock.name


class TestTransactionModel:
    """Tests for the Transaction dataclass."""

    def test_valid_buy_transaction(self):
        t = Transaction(
            portfolio_id=1, stock_id=1,
            type='buy', quantity=10, price=100.0
        )
        assert t.type == 'BUY'   # Should be uppercased

    def test_invalid_type_raises_error(self):
        """Transaction type must be BUY or SELL — anything else fails."""
        with pytest.raises(ValueError, match="must be BUY or SELL"):
            Transaction(
                portfolio_id=1, stock_id=1,
                type='HOLD', quantity=10, price=100.0
            )

    def test_zero_quantity_raises_error(self):
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Transaction(
                portfolio_id=1, stock_id=1,
                type='BUY', quantity=0, price=100.0
            )

    def test_negative_price_raises_error(self):
        with pytest.raises(ValueError, match="Price must be positive"):
            Transaction(
                portfolio_id=1, stock_id=1,
                type='BUY', quantity=10, price=-50.0
            )

    def test_total_value_calculation(self):
        """total_value = quantity * price + fees."""
        t = Transaction(
            portfolio_id=1, stock_id=1, type='BUY',
            quantity=10, price=100.0, fees=5.0
        )
        assert t.total_value == 1005.0

    def test_total_value_with_no_fees(self, sample_transaction):
        # sample_transaction: 10 shares @ 189.50 + 1.99 fees
        expected = round(10 * 189.50 + 1.99, 4)
        assert sample_transaction.total_value == expected


class TestAlertModel:
    """Tests for the Alert dataclass."""

    def test_valid_condition_accepted(self):
        alert = Alert(
            user_id=1, stock_id=1, alert_condition='ABOVE',
            target_price=200.0
        )
        assert alert.alert_condition == 'ABOVE'

    def test_invalid_condition_raises_error(self):
        with pytest.raises(ValueError, match="alert_condition must be one of"):
            Alert(
                user_id=1, stock_id=1,
                alert_condition='SIDEWAYS', target_price=200.0
            )