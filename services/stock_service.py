"""
services/stock_service.py
==========================
Business logic for stock data operations.

Supports searching stocks both from local DB
and globally via Yahoo Finance API.
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

    Uses dependency injection for the repository
    so tests can pass a mock without touching MySQL.
    """

    def __init__(
        self,
        stock_repository: StockRepository = None
    ):
        self.repo = stock_repository or StockRepository()

    def get_all_stocks(self) -> list[Stock]:
        """Returns all active stocks from the database."""

        try:
            stocks = self.repo.find_all()

            logger.info(
                f"Retrieved {len(stocks)} stocks from database."
            )

            return stocks

        except Exception as e:
            logger.error(
                f"Failed to retrieve stocks: {e}"
            )

            return []

    def get_stock(self, symbol: str) -> Optional[Stock]:
        """
        Returns a single stock by symbol.

        Returns None if not found — never raises for missing data.
        """

        symbol = symbol.upper().strip()

        try:
            stock = self.repo.find_by_symbol(symbol)

            if not stock:
                logger.warning(
                    f"Stock not found in database: {symbol}"
                )

            return stock

        except Exception as e:
            logger.error(
                f"Failed to get stock {symbol}: {e}"
            )

            return None

    def search_stocks(self, query: str) -> list[Stock]:
        """
        Searches stocks in local database by symbol or name.

        Returns empty list if query is too short.
        """

        query = query.strip()

        if len(query) < 1:
            return []

        try:
            results = self.repo.search(query)

            logger.debug(
                f"DB search '{query}' returned "
                f"{len(results)} results."
            )

            return results

        except Exception as e:
            logger.error(
                f"Stock search failed for '{query}': {e}"
            )

            return []

    def search_any_stock(self, query: str) -> list[dict]:
        """
        Searches for any stock globally.

        Combines local database results (instant) with
        live Yahoo Finance search results (global coverage).

        Returns a list of dictionaries. Each item contains:

            symbol:
                Ticker symbol

            name:
                Company name

            exchange:
                Exchange name

            type:
                EQUITY / ETF / CRYPTOCURRENCY

            in_database:
                True if already saved in MySQL

            price:
                0.0 (populated later by live fetch)

        Args:
            query:
                Any search term — symbol, company name,
                partial name, crypto name, etc.

                Examples:
                    Tesla
                    AAPL
                    Reliance
                    BTC
                    Samsung
                    Gold ETF
        """

        from api.yahoo_finance_api import YahooFinanceAPI

        query = query.strip()

        if not query or len(query) < 2:
            return []

        results = []
        db_symbols = set()

        # Step 1: Search local database first
        db_stocks = self.search_stocks(query)

        for stock in db_stocks:
            db_symbols.add(stock.symbol)

            results.append(
                {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "exchange": stock.exchange or "",
                    "type": "EQUITY",
                    "in_database": True,
                    "price": 0.0,
                }
            )

        # Step 2: Search Yahoo Finance
        try:
            yahoo_api = YahooFinanceAPI()

            yahoo_results = yahoo_api.search_symbols(query)

            for result in yahoo_results:

                # Skip symbols already found in DB
                if result["symbol"] in db_symbols:
                    continue

                results.append(
                    {
                        "symbol": result["symbol"],
                        "name": result["name"],
                        "exchange": result["exchange"],
                        "type": result["type"],
                        "in_database": False,
                        "price": 0.0,
                    }
                )

        except Exception as e:
            logger.warning(
                f"Yahoo Finance search failed: {e}"
            )

        logger.info(
            f"search_any_stock('{query}') → "
            f"{len(results)} results "
            f"({len(db_symbols)} from DB)"
        )

        return results[:20]

    def get_price_history(
        self,
        symbol: str,
        period_days: int = 365
    ) -> list[dict]:
        """
        Returns historical price data for a stock.

        Args:
            symbol:
                Stock ticker, e.g. 'AAPL'

            period_days:
                How many days of history to return
        """

        stock = self.get_stock(symbol)

        if not stock or not stock.id:
            logger.warning(
                f"Cannot get history — "
                f"stock not found: {symbol}"
            )

            return []

        end_date = datetime.now().strftime("%Y-%m-%d")

        start_date = (
            datetime.now() - timedelta(days=period_days)
        ).strftime("%Y-%m-%d")

        try:
            prices = self.repo.get_historical_prices(
                stock.id,
                start_date,
                end_date
            )

            logger.info(
                f"Retrieved {len(prices)} price records "
                f"for {symbol} "
                f"({start_date} to {end_date})"
            )

            return prices

        except Exception as e:
            logger.error(
                f"Failed to get price history "
                f"for {symbol}: {e}"
            )

            return []

    def get_latest_price(
        self,
        symbol: str
    ) -> Optional[dict]:
        """Returns the most recent price record for a stock."""

        stock = self.get_stock(symbol)

        if not stock or not stock.id:
            return None

        try:
            return self.repo.get_latest_price(stock.id)

        except Exception as e:
            logger.error(
                f"Failed to get latest price "
                f"for {symbol}: {e}"
            )

            return None

    def get_price_change(self, symbol: str) -> dict:
        """
        Calculates the price change between the two most
        recent trading days stored in the database.

        Returns a dictionary containing:

            current_price
            prev_price
            change
            change_pct
            direction (UP/DOWN/FLAT)
        """

        stock = self.get_stock(symbol)

        if not stock or not stock.id:
            return self._empty_price_change()

        try:
            rows = self.repo._execute_query(
                """
                SELECT close_price
                FROM historical_prices
                WHERE stock_id = %s
                ORDER BY price_date DESC
                LIMIT 2
                """,
                (stock.id,)
            )

            if len(rows) < 2:
                return self._empty_price_change()

            current = float(
                rows[0]["close_price"]
            )

            prev = float(
                rows[1]["close_price"]
            )

            change = round(
                current - prev,
                4
            )

            pct = (
                round(
                    (change / prev) * 100,
                    2
                )
                if prev
                else 0
            )

            return {
                "symbol": symbol,
                "current_price": current,
                "prev_price": prev,
                "change": change,
                "change_pct": pct,
                "direction": (
                    "UP"
                    if change > 0
                    else "DOWN"
                    if change < 0
                    else "FLAT"
                ),
            }

        except Exception as e:
            logger.error(
                f"Failed to calculate price change "
                f"for {symbol}: {e}"
            )

            return self._empty_price_change()

    def get_sectors(self) -> list[str]:
        """Returns all unique sectors for filter dropdowns."""

        try:
            return self.repo.get_all_sectors()

        except Exception as e:
            logger.error(
                f"Failed to get sectors: {e}"
            )

            return []

    def save_stock(self, stock: Stock) -> bool:
        """
        Saves or updates a stock in the database.

        Returns:
            True on success.
            False on failure.
        """

        try:
            self.repo.save(stock)

            logger.info(
                f"Stock saved: {stock.symbol}"
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to save stock "
                f"{stock.symbol}: {e}"
            )

            return False

    @staticmethod
    def _empty_price_change() -> dict:
        """Returns a safe empty price change dictionary."""

        return {
            "symbol": "",
            "current_price": 0.0,
            "prev_price": 0.0,
            "change": 0.0,
            "change_pct": 0.0,
            "direction": "FLAT",
        }