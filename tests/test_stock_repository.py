"""
tests/test_stock_repository.py
================================
Tests for StockRepository using a mocked database connection.

WHY MOCK THE DATABASE HERE?
    Repository tests should verify the SQL logic is CORRECT —
    right query, right parameters — without needing a real
    MySQL server running. We mock at the connection level.
"""

import pytest
from unittest.mock import MagicMock, patch
from repositories.stock_repository import StockRepository


class TestStockRepository:

    @patch('repositories.base_repository.DatabaseConnection')
    def test_find_by_symbol_queries_correctly(self, mock_db_conn):
        """
        Verifies find_by_symbol builds the right query and
        correctly converts the result to a Stock object.
        """
        # Arrange — set up the fake database response
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{
            'id': 1, 'symbol': 'AAPL', 'name': 'Apple Inc.',
            'sector': 'Technology', 'is_active': 1,
        }]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.get_connection.return_value = mock_conn

        repo = StockRepository()

        # Act
        result = repo.find_by_symbol('aapl')

        # Assert
        assert result is not None
        assert result.symbol == 'AAPL'
        assert result.name == 'Apple Inc.'

        # Verify the query was executed with uppercase symbol
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == ('AAPL',)

    @patch('repositories.base_repository.DatabaseConnection')
    def test_find_by_symbol_returns_none_when_not_found(self, mock_db_conn):
        """When no rows match, should return None — not raise an error."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.get_connection.return_value = mock_conn

        repo = StockRepository()
        result = repo.find_by_symbol('NONEXISTENT')

        assert result is None

    @patch('repositories.base_repository.DatabaseConnection')
    def test_search_uses_wildcard_pattern(self, mock_db_conn):
        """Search should wrap the query in % wildcards for LIKE."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.get_connection.return_value = mock_conn

        repo = StockRepository()
        repo.search('app')

        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert params[0] == '%APP%'

    @patch('repositories.base_repository.DatabaseConnection')
    def test_save_calls_commit_on_success(self, mock_db_conn):
        """A successful write must call conn.commit()."""
        from models.stock import Stock

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.get_connection.return_value = mock_conn

        repo = StockRepository()
        stock = Stock(symbol='NFLX', name='Netflix Inc.')
        repo.save(stock)

        mock_conn.commit.assert_called_once()

    @patch('repositories.base_repository.DatabaseConnection')
    def test_save_calls_rollback_on_failure(self, mock_db_conn):
        """A failed write must call conn.rollback(), not commit()."""
        from models.stock import Stock

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.get_connection.return_value = mock_conn

        repo = StockRepository()
        stock = Stock(symbol='NFLX', name='Netflix Inc.')

        with pytest.raises(Exception):
            repo.save(stock)

        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()