"""
tests/test_stock_controller.py
================================
Tests for StockController — verifying the GUI-facing
contract (success/message/data shape) is always honoured.
"""

import pytest
from unittest.mock import MagicMock
from controllers.stock_controller import StockController


@pytest.fixture
def mock_stock_service(sample_stock, sample_stock_list):
    service = MagicMock()
    service.get_stock.return_value = sample_stock
    service.search_stocks.return_value = [sample_stock]
    service.get_all_stocks.return_value = sample_stock_list
    return service


class TestStockController:

    def test_search_empty_query_returns_failure(self, mock_stock_service):
        controller = StockController(stock_service=mock_stock_service)
        result = controller.search('')

        assert result['success'] is False
        assert 'enter' in result['message'].lower()

    def test_search_query_too_long_returns_failure(self, mock_stock_service):
        controller = StockController(stock_service=mock_stock_service)
        result = controller.search('A' * 25)

        assert result['success'] is False

    def test_search_success_returns_data(self, mock_stock_service):
        controller = StockController(stock_service=mock_stock_service)
        result = controller.search('AAPL')

        assert result['success'] is True
        assert result['count'] == 1
        assert result['data'][0]['symbol'] == 'AAPL'

    def test_search_no_results_returns_failure_message(
        self, mock_stock_service
    ):
        mock_stock_service.search_stocks.return_value = []
        controller = StockController(stock_service=mock_stock_service)

        result = controller.search('ZZZZZ')

        assert result['success'] is False
        assert 'No stocks found' in result['message']

    def test_get_stock_detail_not_found(self, mock_stock_service):
        mock_stock_service.get_stock.return_value = None
        controller = StockController(stock_service=mock_stock_service)

        result = controller.get_stock_detail('FAKESYM')

        assert result['success'] is False

    def test_get_stock_detail_success(self, mock_stock_service):
        controller = StockController(stock_service=mock_stock_service)
        result = controller.get_stock_detail('AAPL')

        assert result['success'] is True
        assert result['data']['symbol'] == 'AAPL'

    def test_get_price_history_invalid_period_defaults_to_365(
        self, mock_stock_service
    ):
        """An invalid period (e.g. 999) should fall back to 365 days."""
        mock_stock_service.get_price_history.return_value = []
        controller = StockController(stock_service=mock_stock_service)

        controller.get_price_history('AAPL', period_days=999)

        # Verify service was called with the corrected default
        call_args = mock_stock_service.get_price_history.call_args
        assert call_args[0][1] == 365

    def test_result_always_has_required_keys(self, mock_stock_service):
        """
        Every controller method must return a dict with these
        exact keys — the GUI relies on this contract everywhere.
        """
        controller = StockController(stock_service=mock_stock_service)
        result = controller.search('AAPL')

        required_keys = {'success', 'message', 'data', 'count'}
        assert required_keys.issubset(result.keys())