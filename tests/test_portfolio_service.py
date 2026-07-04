"""
tests/test_portfolio_service.py
=================================
Tests for PortfolioService — particularly the P&L calculation
logic, which is the most business-critical code in the app.
"""

import pytest
from unittest.mock import MagicMock
from services.portfolio_service import PortfolioService


@pytest.fixture
def mock_portfolio_repo():
    return MagicMock()


@pytest.fixture
def mock_stock_repo_for_portfolio(sample_stock):
    repo = MagicMock()
    repo.find_by_symbol.return_value = sample_stock
    return repo


class TestPortfolioService:

    def test_add_transaction_rejects_unknown_stock(
        self, mock_portfolio_repo, mock_stock_repo_for_portfolio
    ):
        """Should refuse to record a transaction for a stock
        that doesn't exist in the database."""
        mock_stock_repo_for_portfolio.find_by_symbol.return_value = None

        service = PortfolioService(
            portfolio_repository=mock_portfolio_repo,
            stock_repository=mock_stock_repo_for_portfolio,
        )

        result = service.add_transaction(
            portfolio_id=1, symbol='FAKESTOCK',
            transaction_type='BUY', quantity=10, price=100.0
        )

        assert result is False
        mock_portfolio_repo.save_transaction.assert_not_called()

    def test_add_transaction_buy_succeeds(
        self, mock_portfolio_repo, mock_stock_repo_for_portfolio
    ):
        service = PortfolioService(
            portfolio_repository=mock_portfolio_repo,
            stock_repository=mock_stock_repo_for_portfolio,
        )

        result = service.add_transaction(
            portfolio_id=1, symbol='AAPL',
            transaction_type='BUY', quantity=10, price=189.50
        )

        assert result is True
        mock_portfolio_repo.save_transaction.assert_called_once()

    def test_sell_more_than_held_is_rejected(
        self, mock_portfolio_repo, mock_stock_repo_for_portfolio
    ):
        """
        Critical business rule: cannot sell more shares than
        currently held. This test ensures that rule is enforced.
        """
        mock_portfolio_repo.get_holdings.return_value = [
            {'symbol': 'AAPL', 'shares_held': 5.0}
        ]

        service = PortfolioService(
            portfolio_repository=mock_portfolio_repo,
            stock_repository=mock_stock_repo_for_portfolio,
        )

        # Try to sell 10 shares when only 5 are held
        result = service.add_transaction(
            portfolio_id=1, symbol='AAPL',
            transaction_type='SELL', quantity=10, price=200.0
        )

        assert result is False
        mock_portfolio_repo.save_transaction.assert_not_called()

    def test_sell_within_holdings_succeeds(
        self, mock_portfolio_repo, mock_stock_repo_for_portfolio
    ):
        mock_portfolio_repo.get_holdings.return_value = [
            {'symbol': 'AAPL', 'shares_held': 10.0}
        ]

        service = PortfolioService(
            portfolio_repository=mock_portfolio_repo,
            stock_repository=mock_stock_repo_for_portfolio,
        )

        result = service.add_transaction(
            portfolio_id=1, symbol='AAPL',
            transaction_type='SELL', quantity=5, price=200.0
        )

        assert result is True

    def test_portfolio_summary_calculates_pnl_correctly(
        self, mock_portfolio_repo, mock_stock_repo_for_portfolio
    ):
        """
        Verifies the P&L math by hand:
        10 shares bought at $150 avg = $1500 invested.
        Current price $180 → market value $1800.
        P&L = $1800 - $1500 = $300.
        P&L % = 300 / 1500 * 100 = 20%.
        """
        mock_portfolio_repo.get_holdings.return_value = [{
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.',
            'shares_held': 10.0,
            'avg_cost': 150.0,
            'total_invested': 1500.0,
        }]

        service = PortfolioService(
            portfolio_repository=mock_portfolio_repo,
            stock_repository=mock_stock_repo_for_portfolio,
        )

        summary = service.get_portfolio_summary(
            portfolio_id=1,
            current_prices={'AAPL': 180.0}
        )

        assert summary['total_invested'] == 1500.0
        assert summary['current_value']  == 1800.0
        assert summary['total_pnl']      == 300.0
        assert summary['total_pnl_pct']  == 20.0

    def test_portfolio_summary_handles_loss(
        self, mock_portfolio_repo, mock_stock_repo_for_portfolio
    ):
        """Verify negative P&L is calculated correctly too."""
        mock_portfolio_repo.get_holdings.return_value = [{
            'symbol': 'TSLA',
            'stock_name': 'Tesla Inc.',
            'shares_held': 5.0,
            'avg_cost': 300.0,
            'total_invested': 1500.0,
        }]

        service = PortfolioService(
            portfolio_repository=mock_portfolio_repo,
            stock_repository=mock_stock_repo_for_portfolio,
        )

        summary = service.get_portfolio_summary(
            portfolio_id=1,
            current_prices={'TSLA': 250.0}   # Price dropped
        )

        assert summary['total_pnl'] == -250.0
        assert summary['total_pnl_pct'] == pytest.approx(-16.67, abs=0.01)

    def test_portfolio_summary_empty_holdings(
        self, mock_portfolio_repo, mock_stock_repo_for_portfolio
    ):
        """Empty portfolio should return zeros, not crash."""
        mock_portfolio_repo.get_holdings.return_value = []

        service = PortfolioService(
            portfolio_repository=mock_portfolio_repo,
            stock_repository=mock_stock_repo_for_portfolio,
        )

        summary = service.get_portfolio_summary(
            portfolio_id=1, current_prices={}
        )

        assert summary['total_invested'] == 0.0
        assert summary['current_value']  == 0.0
        assert summary['holdings']       == []