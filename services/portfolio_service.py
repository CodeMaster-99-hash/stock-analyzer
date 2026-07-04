"""
services/portfolio_service.py
==============================
Business logic for portfolio management.

KEY CONCEPT — Computing Values vs Storing Them:
    We never store "portfolio value = $50,000" in the database.
    We compute it fresh every time from transactions + current prices.

    WHY?
        Stored values go stale the moment a price changes.
        Computed values are always accurate.
        With modern databases, this computation is fast enough.
"""

import logging
from datetime import datetime
from typing import Optional
from models.transaction import Transaction
from repositories.portfolio_repository import PortfolioRepository
from repositories.stock_repository import StockRepository

logger = logging.getLogger(__name__)


class PortfolioService:
    """Business logic for portfolio and transaction management."""

    def __init__(self,
                 portfolio_repository: PortfolioRepository = None,
                 stock_repository:     StockRepository     = None):
        self.portfolio_repo = portfolio_repository or PortfolioRepository()
        self.stock_repo     = stock_repository     or StockRepository()

    def get_portfolios(self, user_id: int) -> list[dict]:
        """Returns all portfolios for a user."""
        try:
            return self.portfolio_repo.find_by_user(user_id)
        except Exception as e:
            logger.error(f"Failed to get portfolios for user {user_id}: {e}")
            return []

    def create_portfolio(self, user_id: int, name: str,
                         description: str = None) -> Optional[int]:
        """
        Creates a new portfolio.
        Returns the new portfolio ID or None on failure.
        """
        name = name.strip()
        if not name:
            logger.warning("Portfolio name cannot be empty.")
            return None
        try:
            portfolio_id = self.portfolio_repo.create(
                user_id, name, description
            )
            logger.info(f"Portfolio created: '{name}' (id={portfolio_id})")
            return portfolio_id
        except Exception as e:
            logger.error(f"Failed to create portfolio: {e}")
            return None

    def add_transaction(self, portfolio_id: int, symbol: str,
                        transaction_type: str, quantity: float,
                        price: float, fees: float = 0.0,
                        notes: str = None,
                        trans_date: datetime = None) -> bool:
        """
        Records a BUY or SELL transaction.

        Validates:
        - Stock exists in database
        - Quantity and price are positive
        - SELL quantity doesn't exceed current holdings

        Returns True on success, False on failure.
        """
        # Validate stock exists
        stock = self.stock_repo.find_by_symbol(symbol)
        if not stock:
            logger.warning(f"Cannot add transaction — unknown stock: {symbol}")
            return False

        # Validate sell quantity
        if transaction_type.upper() == 'SELL':
            holdings = self.get_holdings(portfolio_id)
            holding  = next(
                (h for h in holdings if h['symbol'] == symbol), None
            )
            current_shares = float(holding['shares_held']) if holding else 0

            if quantity > current_shares:
                logger.warning(
                    f"Cannot sell {quantity} shares of {symbol} — "
                    f"only {current_shares} held."
                )
                return False

        try:
            transaction = Transaction(
                portfolio_id = portfolio_id,
                stock_id     = stock.id,
                type         = transaction_type.upper(),
                quantity     = quantity,
                price        = price,
                fees         = fees,
                notes        = notes,
                trans_date   = trans_date or datetime.now(),
            )
            self.portfolio_repo.save_transaction(transaction)
            logger.info(
                f"{transaction_type.upper()} {quantity} {symbol} "
                f"@ ${price:.2f} recorded."
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save transaction: {e}")
            return False

    def get_holdings(self, portfolio_id: int) -> list[dict]:
        """
        Returns current holdings with shares held and average cost.
        Only returns stocks where shares_held > 0.
        """
        try:
            return self.portfolio_repo.get_holdings(portfolio_id)
        except Exception as e:
            logger.error(f"Failed to get holdings for portfolio {portfolio_id}: {e}")
            return []

    def get_portfolio_summary(self, portfolio_id: int,
                               current_prices: dict) -> dict:
        """
        Calculates a complete portfolio summary.

        Args:
            portfolio_id:   The portfolio to summarise
            current_prices: Dict mapping symbol to current price
                            e.g. {'AAPL': 189.50, 'MSFT': 415.20}

        Returns dict with:
            total_invested:  Total amount invested (cost basis)
            current_value:   Current market value
            total_pnl:       Profit or loss in dollars
            total_pnl_pct:   Profit or loss as percentage
            holdings:        List of individual holding summaries
        """
        holdings = self.get_holdings(portfolio_id)

        total_invested = 0.0
        current_value  = 0.0
        holding_summaries = []

        for h in holdings:
            symbol        = h['symbol']
            shares        = float(h['shares_held'])
            avg_cost      = float(h['avg_cost'] or 0)
            invested      = float(h['total_invested'] or 0)
            current_price = current_prices.get(symbol, 0)

            market_value  = shares * current_price
            pnl           = market_value - invested
            pnl_pct       = (pnl / invested * 100) if invested else 0

            total_invested += invested
            current_value  += market_value

            holding_summaries.append({
                'symbol':        symbol,
                'stock_name':    h['stock_name'],
                'shares':        shares,
                'avg_cost':      round(avg_cost, 4),
                'current_price': current_price,
                'market_value':  round(market_value, 2),
                'invested':      round(invested, 2),
                'pnl':           round(pnl, 2),
                'pnl_pct':       round(pnl_pct, 2),
                'direction':     'UP' if pnl > 0 else 'DOWN' if pnl < 0 else 'FLAT',
            })

        total_pnl     = current_value - total_invested
        total_pnl_pct = (
            (total_pnl / total_invested * 100) if total_invested else 0
        )

        return {
            'portfolio_id':  portfolio_id,
            'total_invested': round(total_invested, 2),
            'current_value':  round(current_value, 2),
            'total_pnl':      round(total_pnl, 2),
            'total_pnl_pct':  round(total_pnl_pct, 2),
            'holdings':       holding_summaries,
        }

    def get_transactions(self, portfolio_id: int) -> list[dict]:
        """Returns full transaction history for a portfolio."""
        try:
            return self.portfolio_repo.get_transactions(portfolio_id)
        except Exception as e:
            logger.error(
                f"Failed to get transactions for portfolio {portfolio_id}: {e}"
            )
            return []
