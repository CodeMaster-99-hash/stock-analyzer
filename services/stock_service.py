"""
services/stock_service.py
==========================
Business logic for stock data operations.

This service sits between the controller and the repository.
It decides WHEN to fetch from API vs read from database,
and HOW to process the data before returning it.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from models.stock import Stock
from repositories.stock_repository import StockRepository

logger = logging.getLogger(__name__)


class StockService:
    """
    Handles all business logic related to stocks.

    WHY INJECT THE REPOSITORY?
        We pass the repository in via __init__ instead of
        creating it inside the class. This is called
        Dependency Injection.

        Benefits:
        1. Testing — we can pass a fake repository in tests
           without touching the real database.
        2. Flexibility — we can swap MySQL for another database
           by passing a different repository.
    """

    def __init__(self, stock_repository: StockRepository = None):
        self.repo = stock_repository or StockRepository()

    def get_all_stocks(self) -> list[Stock]:
        """
        Returns all active stocks.
        Used to populate search dropdowns in the GUI.
        """
        try:
            stocks = self.repo.find_all()
            logger.info(f"Retrieved {len(stocks)} stocks from database.")
            return stocks
        except Exception as e:
            logger.error(f"Failed to retrieve stocks: {e}")
            return []

    def get_stock(self, symbol: str) -> Optional[Stock]:
        """
        Returns a single stock by symbol.
        Returns None if the stock is not found.
        """
        symbol = symbol.upper().strip()
        try:
            stock = self.repo.find_by_symbol(symbol)
            if not stock:
                logger.warning(f"Stock not found in database: {symbol}")
            return stock
        except Exception as e:
            logger.error(f"Failed to get stock {symbol}: {e}")
            return None

    def search_stocks(self, query: str) -> list[Stock]:
        """
        Searches stocks by symbol or name.
        Returns empty list if query is too short.
        """
        query = query.strip()
        if len(query) < 1:
            return []
        try:
            results = self.repo.search(query)
            logger.debug(f"Search '{query}' returned {len(results)} results.")
            return results
        except Exception as e:
            logger.error(f"Stock search failed for '{query}': {e}")
            return []

    def get_price_history(self, symbol: str,
                          period_days: int = 365) -> list[dict]:
        """
        Returns historical price data for a stock.

        Args:
            symbol:      Stock ticker e.g. 'AAPL'
            period_days: How many days of history to return

        Returns:
            List of price dicts ordered by date ascending.
            Empty list if stock not found or no data available.
        """
        stock = self.get_stock(symbol)
        if not stock or not stock.id:
            logger.warning(f"Cannot get history — stock not found: {symbol}")
            return []

        end_date   = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=period_days)
                      ).strftime('%Y-%m-%d')

        try:
            prices = self.repo.get_historical_prices(
                stock.id, start_date, end_date
            )
            logger.info(
                f"Retrieved {len(prices)} price records for {symbol} "
                f"({start_date} to {end_date})"
            )
            return prices
        except Exception as e:
            logger.error(f"Failed to get price history for {symbol}: {e}")
            return []

    def get_latest_price(self, symbol: str) -> Optional[dict]:
        """
        Returns the most recent price record for a stock.
        Returns None if no price data exists.
        """
        stock = self.get_stock(symbol)
        if not stock or not stock.id:
            return None
        try:
            return self.repo.get_latest_price(stock.id)
        except Exception as e:
            logger.error(f"Failed to get latest price for {symbol}: {e}")
            return None

    def get_price_change(self, symbol: str) -> dict:
        """
        Calculates the price change and percentage change
        between the two most recent trading days.

        Returns a dict with:
            current_price:  Latest closing price
            prev_price:     Previous day closing price
            change:         Absolute change (current - prev)
            change_pct:     Percentage change
            direction:      'UP', 'DOWN', or 'FLAT'
        """
        stock = self.get_stock(symbol)
        if not stock or not stock.id:
            return self._empty_price_change()

        try:
            rows = self.repo._execute_query(
                """SELECT close_price FROM historical_prices
                   WHERE stock_id = %s
                   ORDER BY price_date DESC
                   LIMIT 2""",
                (stock.id,)
            )

            if len(rows) < 2:
                return self._empty_price_change()

            current = float(rows[0]['close_price'])
            prev    = float(rows[1]['close_price'])
            change  = round(current - prev, 4)
            pct     = round((change / prev) * 100, 2) if prev else 0

            return {
                'symbol':        symbol,
                'current_price': current,
                'prev_price':    prev,
                'change':        change,
                'change_pct':    pct,
                'direction':     'UP' if change > 0 else 'DOWN' if change < 0 else 'FLAT',
            }
        except Exception as e:
            logger.error(f"Failed to calculate price change for {symbol}: {e}")
            return self._empty_price_change()

    def get_sectors(self) -> list[str]:
        """Returns all unique sectors for filter dropdowns."""
        try:
            return self.repo.get_all_sectors()
        except Exception as e:
            logger.error(f"Failed to get sectors: {e}")
            return []

    def save_stock(self, stock: Stock) -> bool:
        """
        Saves or updates a stock in the database.
        Returns True on success, False on failure.
        """
        try:
            self.repo.save(stock)
            logger.info(f"Stock saved: {stock.symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to save stock {stock.symbol}: {e}")
            return False

    @staticmethod
    def _empty_price_change() -> dict:
        """Returns a safe empty price change dict."""
        return {
            'symbol':        '',
            'current_price': 0.0,
            'prev_price':    0.0,
            'change':        0.0,
            'change_pct':    0.0,
            'direction':     'FLAT',
        }
