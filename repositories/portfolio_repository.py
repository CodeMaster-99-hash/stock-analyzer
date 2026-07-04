"""
repositories/portfolio_repository.py
=====================================
Database operations for portfolios and transactions.
"""

import logging
from typing import Optional
from models.portfolio import Portfolio
from models.transaction import Transaction
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PortfolioRepository(BaseRepository):
    """Handles all database operations for portfolios and transactions."""

    def find_by_user(self, user_id: int) -> list[dict]:
        """Returns all portfolios belonging to a user."""
        return self._execute_query(
            "SELECT * FROM portfolio WHERE user_id = %s ORDER BY name",
            (user_id,)
        )

    def find_by_id(self, portfolio_id: int) -> Optional[dict]:
        """Returns a single portfolio by ID."""
        rows = self._execute_query(
            "SELECT * FROM portfolio WHERE id = %s",
            (portfolio_id,)
        )
        return rows[0] if rows else None

    def create(self, user_id: int, name: str,
               description: str = None) -> int:
        """Creates a new portfolio and returns its new ID."""
        return self._execute_write(
            """INSERT INTO portfolio (user_id, name, description)
               VALUES (%s, %s, %s)""",
            (user_id, name, description)
        )

    def save_transaction(self, transaction: Transaction) -> int:
        """Records a buy or sell transaction."""
        return self._execute_write(
            """INSERT INTO transactions
               (portfolio_id, stock_id, type, quantity,
                price, fees, notes, trans_date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                transaction.portfolio_id,
                transaction.stock_id,
                transaction.type,
                transaction.quantity,
                transaction.price,
                transaction.fees,
                transaction.notes,
                transaction.trans_date,
            )
        )

    def get_transactions(self, portfolio_id: int) -> list[dict]:
        """
        Returns all transactions for a portfolio joined with stock info.
        We JOIN with stocks so we get symbol and name in one query
        instead of making a separate query for each transaction.
        """
        return self._execute_query(
            """SELECT t.*, s.symbol, s.name as stock_name
               FROM transactions t
               JOIN stocks s ON t.stock_id = s.id
               WHERE t.portfolio_id = %s
               ORDER BY t.trans_date DESC""",
            (portfolio_id,)
        )

    def get_holdings(self, portfolio_id: int) -> list[dict]:
        """
        Calculates current holdings by aggregating all transactions.

        This is the core portfolio query — it sums all BUY quantities
        and subtracts SELL quantities, giving current shares held.
        It also calculates the average buy price (cost basis).

        SUM(CASE WHEN type='BUY' ...) is SQL's way of doing an
        if/else inside an aggregation.
        """
        return self._execute_query(
            """SELECT
                s.id          AS stock_id,
                s.symbol,
                s.name        AS stock_name,
                s.sector,
                SUM(CASE WHEN t.type = 'BUY'
                    THEN t.quantity ELSE -t.quantity END)  AS shares_held,
                SUM(CASE WHEN t.type = 'BUY'
                    THEN t.quantity * t.price ELSE 0 END)
                / NULLIF(SUM(CASE WHEN t.type = 'BUY'
                    THEN t.quantity ELSE 0 END), 0)        AS avg_cost,
                SUM(CASE WHEN t.type = 'BUY'
                    THEN t.quantity * t.price + t.fees
                    ELSE -(t.quantity * t.price - t.fees) END) AS total_invested
               FROM transactions t
               JOIN stocks s ON t.stock_id = s.id
               WHERE t.portfolio_id = %s
               GROUP BY s.id, s.symbol, s.name, s.sector
               HAVING shares_held > 0
               ORDER BY s.symbol""",
            (portfolio_id,)
        )
