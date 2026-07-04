"""
controllers/portfolio_controller.py
=====================================
Bridges the GUI and PortfolioService.
"""

import logging
from services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)

# Default user ID until we build proper authentication in Phase 8
DEFAULT_USER_ID = 1


class PortfolioController:
    """
    Handles all GUI interactions related to portfolios.

    USAGE IN GUI (Phase 8):
        self.ctrl = PortfolioController()

        # Load user portfolios on startup:
        result = self.ctrl.get_portfolios()

        # When user adds a transaction:
        result = self.ctrl.add_transaction(
            portfolio_id=1, symbol='AAPL',
            transaction_type='BUY', quantity=10, price=189.50
        )
    """

    def __init__(self, portfolio_service: PortfolioService = None):
        self.service = portfolio_service or PortfolioService()

    def get_portfolios(self, user_id: int = DEFAULT_USER_ID) -> dict:
        """Returns all portfolios for the current user."""
        portfolios = self.service.get_portfolios(user_id)
        return {
            'success': True,
            'data':    portfolios,
            'count':   len(portfolios),
            'message': f"{len(portfolios)} portfolio(s) loaded."
        }

    def create_portfolio(self, name: str,
                         description: str = None,
                         user_id: int = DEFAULT_USER_ID) -> dict:
        """
        Creates a new portfolio.
        Called when user clicks 'New Portfolio' in the GUI.
        """
        name = name.strip()
        if not name:
            return {
                'success': False,
                'message': "Portfolio name cannot be empty.",
                'data':    None
            }

        portfolio_id = self.service.create_portfolio(
            user_id, name, description
        )

        if not portfolio_id:
            return {
                'success': False,
                'message': "Failed to create portfolio. Please try again.",
                'data':    None
            }

        return {
            'success': True,
            'message': f"Portfolio '{name}' created successfully.",
            'data':    {'id': portfolio_id, 'name': name}
        }

    def add_transaction(self, portfolio_id: int, symbol: str,
                        transaction_type: str, quantity: float,
                        price: float, fees: float = 0.0,
                        notes: str = None) -> dict:
        """
        Records a buy or sell transaction.
        Called when user submits the Add Transaction form.
        """
        # Input validation before hitting the service
        if quantity <= 0:
            return {
                'success': False,
                'message': "Quantity must be greater than zero.",
                'data':    None
            }

        if price <= 0:
            return {
                'success': False,
                'message': "Price must be greater than zero.",
                'data':    None
            }

        if transaction_type.upper() not in ('BUY', 'SELL'):
            return {
                'success': False,
                'message': "Transaction type must be BUY or SELL.",
                'data':    None
            }

        success = self.service.add_transaction(
            portfolio_id    = portfolio_id,
            symbol          = symbol.upper(),
            transaction_type= transaction_type,
            quantity        = quantity,
            price           = price,
            fees            = fees,
            notes           = notes,
        )

        if not success:
            return {
                'success': False,
                'message': f"Failed to record {transaction_type} transaction. "
                           f"Check you have enough shares to sell.",
                'data':    None
            }

        return {
            'success': True,
            'message': f"Successfully recorded {transaction_type.upper()} "
                       f"{quantity} {symbol.upper()} @ ${price:.2f}.",
            'data':    None
        }

    def get_holdings(self, portfolio_id: int) -> dict:
        """
        Returns current holdings for display in the portfolio table.
        """
        holdings = self.service.get_holdings(portfolio_id)
        return {
            'success': True,
            'data':    holdings,
            'count':   len(holdings),
            'message': f"{len(holdings)} position(s) held."
        }

    def get_portfolio_summary(self, portfolio_id: int,
                               current_prices: dict) -> dict:
        """
        Returns the full portfolio summary including P&L.
        Called whenever the portfolio tab is opened or refreshed.
        """
        summary = self.service.get_portfolio_summary(
            portfolio_id, current_prices
        )
        return {
            'success': True,
            'data':    summary,
            'message': "Portfolio summary loaded."
        }

    def get_transactions(self, portfolio_id: int) -> dict:
        """Returns full transaction history for the history tab."""
        transactions = self.service.get_transactions(portfolio_id)
        return {
            'success': True,
            'data':    transactions,
            'count':   len(transactions),
            'message': f"{len(transactions)} transaction(s) found."
        }
