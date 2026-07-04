"""
tests/test_stock_service.py
=============================
Tests for StockService using a mocked repository.

WHY MOCK THE REPOSITORY (NOT THE DATABASE)?
    The service layer doesn't know about SQL — it only knows
    about the repository's interface. We mock at that boundary,
    which matches the dependency injection pattern we built
    the service with.
"""

import pytest
from services.stock_service import StockService


class TestStockService:

    def test_get_stock_returns_stock_when_found(
        self, mock_stock_repository
    ):
        service = StockService(stock_repository=mock_stock_repository)
        result = service.get_stock('AAPL')

        assert result is not None
        assert result.symbol == 'AAPL'
        mock_stock_repository.find_by_symbol.assert_called_once_with('AAPL')

    def test_get_stock_returns_none_when_not_found(
        self, mock_stock_repository
    ):
        mock_stock_repository.find_by_symbol.return_value = None
        service = StockService(stock_repository=mock_stock_repository)

        result = service.get_stock('NONEXISTENT')
        assert result is None

    def test_get_stock_handles_repository_exception(
        self, mock_stock_repository
    ):
        """
        If the repository throws an exception, the service must
        catch it and return None — never let the GUI crash.
        """
        mock_stock_repository.find_by_symbol.side_effect = Exception(
            "Connection lost"
        )
        service = StockService(stock_repository=mock_stock_repository)

        result = service.get_stock('AAPL')
        assert result is None   # Graceful failure, not a crash

    def test_search_stocks_empty_query_returns_empty_list(
        self, mock_stock_repository
    ):
        service = StockService(stock_repository=mock_stock_repository)
        result = service.search_stocks('')
        assert result == []
        # Repository should never even be called for empty query
        mock_stock_repository.search.assert_not_called()

    def test_search_stocks_calls_repository(
        self, mock_stock_repository
    ):
        service = StockService(stock_repository=mock_stock_repository)
        result = service.search_stocks('AAPL')

        assert len(result) == 1
        mock_stock_repository.search.assert_called_once_with('AAPL')

    def test_get_all_stocks_returns_list(self, mock_stock_repository):
        service = StockService(stock_repository=mock_stock_repository)
        result = service.get_all_stocks()
        assert len(result) == 3

    def test_get_all_stocks_returns_empty_on_failure(
        self, mock_stock_repository
    ):
        mock_stock_repository.find_all.side_effect = Exception("DB down")
        service = StockService(stock_repository=mock_stock_repository)

        result = service.get_all_stocks()
        assert result == []   # Never crashes, returns safe empty list

    def test_save_stock_returns_true_on_success(
        self, mock_stock_repository, sample_stock
    ):
        service = StockService(stock_repository=mock_stock_repository)
        result = service.save_stock(sample_stock)
        assert result is True

    def test_save_stock_returns_false_on_failure(
        self, mock_stock_repository, sample_stock
    ):
        mock_stock_repository.save.side_effect = Exception("Write failed")
        service = StockService(stock_repository=mock_stock_repository)

        result = service.save_stock(sample_stock)
        assert result is False