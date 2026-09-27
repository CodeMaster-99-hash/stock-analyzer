"""
controllers/stock_controller.py
================================
Bridges the GUI and StockService.

Every method returns a standard result dict so the
GUI always handles the same shape — never raw exceptions.

Standard result dict:
    {
        'success': True/False,
        'message': human-readable string,
        'data': list, dict, or None,
        'count': int (number of results),
    }
"""

import logging
from services.stock_service import StockService


logger = logging.getLogger(__name__)


class StockController:
    """
    Handles all GUI interactions related to stocks.

    USAGE IN GUI:

        ctrl = StockController()

        # Search local DB:
        result = ctrl.search('AAPL')

        # Search globally (DB + Yahoo Finance):
        result = ctrl.search_global('Tesla')

        # Fetch a new stock and save to DB:
        result = ctrl.fetch_and_load_stock('RELIANCE.NS')

        # Get stock detail:
        result = ctrl.get_stock_detail('AAPL')
    """

    def __init__(
        self,
        stock_service: StockService = None
    ):
        self.service = stock_service or StockService()

    # ─────────────────────────────────────────────────────────────
    # Local DB Search
    # ─────────────────────────────────────────────────────────────

    def search(self, query: str) -> dict:
        """
        Searches stocks in local database by symbol or name.

        Fast — no network call.
        Returns only stocks already saved.
        """

        query = query.strip()

        if not query:
            return self._result(
                success=False,
                message="Please enter a stock symbol or name.",
                data=[]
            )

        if len(query) > 20:
            return self._result(
                success=False,
                message="Search query is too long.",
                data=[]
            )

        stocks = self.service.search_stocks(query)

        data = [
            stock.to_dict()
            for stock in stocks
        ]

        if not data:
            return self._result(
                success=False,
                message=f"No stocks found matching '{query}'.",
                data=[]
            )

        return self._result(
            success=True,
            message=(
                f"Found {len(data)} result(s) "
                f"for '{query}'."
            ),
            data=data,
            count=len(data)
        )

    # ─────────────────────────────────────────────────────────────
    # Global Search (DB + Yahoo Finance)
    # ─────────────────────────────────────────────────────────────

    def search_global(self, query: str) -> dict:
        """
        Searches for any stock globally.

        Combines local database results with
        live Yahoo Finance search.

        Results include both stocks already in our DB
        and new stocks from any world market.

        Each result has:

            symbol:
                Ticker

            name:
                Company name

            exchange:
                e.g. NASDAQ, NSE, LSE

            type:
                EQUITY / ETF / CRYPTOCURRENCY

            in_database:
                True if already in MySQL

            price:
                0.0 (fetched separately)

        Args:
            query:
                Any search term such as:
                'Tesla', 'AAPL', 'Reliance',
                'BTC', 'Gold ETF'
        """

        query = query.strip()

        if not query:
            return self._result(
                success=False,
                message="Please enter a stock symbol or name.",
                data=[]
            )

        if len(query) < 2:
            return self._result(
                success=False,
                message="Please enter at least 2 characters.",
                data=[]
            )

        results = self.service.search_any_stock(query)

        if not results:
            return self._result(
                success=False,
                message=(
                    f"No stocks found for '{query}'. "
                    f"Try the exact ticker symbol "
                    f"(e.g. AAPL, TSLA)."
                ),
                data=[]
            )

        return self._result(
            success=True,
            message=(
                f"Found {len(results)} results "
                f"for '{query}'"
            ),
            data=results,
            count=len(results)
        )

    # ─────────────────────────────────────────────────────────────
    # Fetch New Stock
    # ─────────────────────────────────────────────────────────────

    def fetch_and_load_stock(self, symbol: str) -> dict:
        """
        Fetches a stock from Yahoo Finance and saves it to DB.

        Called when user selects a stock not yet in the database.

        This makes any stock searchable and chartable:
        US, Indian, European, crypto, ETF, etc.

        Args:
            symbol:
                Valid Yahoo Finance symbol.

                Examples:
                    RELIANCE.NS
                    BTC-USD
                    ASML.AS
        """

        symbol = symbol.upper().strip()

        if not symbol:
            return self._result(
                success=False,
                message="No symbol provided."
            )

        from services.data_fetcher_service import (
            DataFetcherService
        )

        fetcher = DataFetcherService()

        result = fetcher.fetch_any_stock(symbol)

        return self._result(
            success=result.get("success", False),
            message=result.get("message", ""),
            data=result
        )

    # ─────────────────────────────────────────────────────────────
    # Stock Detail
    # ─────────────────────────────────────────────────────────────

    def get_stock_detail(self, symbol: str) -> dict:
        """
        Returns full details for a single stock from the DB.

        Called when the user clicks on a stock to view it.
        """

        symbol = symbol.upper().strip()

        if not symbol:
            return self._result(
                success=False,
                message="No symbol provided."
            )

        stock = self.service.get_stock(symbol)

        if not stock:
            return self._result(
                success=False,
                message=(
                    f"{symbol} was not found in the database. "
                    f"Search for it to add it automatically."
                )
            )

        return self._result(
            success=True,
            message=f"Loaded {symbol}.",
            data=stock.to_dict()
        )

    # ─────────────────────────────────────────────────────────────
    # Price History
    # ─────────────────────────────────────────────────────────────

    def get_price_history(
        self,
        symbol: str,
        period_days: int = 365
    ) -> dict:
        """
        Returns historical price data formatted for charting.

        Args:
            symbol:
                Stock ticker.

            period_days:
                30, 90, 180, 365, 730, 1825
        """

        valid_periods = {
            30,
            90,
            180,
            365,
            730,
            1825
        }

        if period_days not in valid_periods:
            period_days = 365

        prices = self.service.get_price_history(
            symbol,
            period_days
        )

        if not prices:
            return self._result(
                success=False,
                message=(
                    f"No price history found for {symbol}. "
                    f"Fetch data from API first."
                ),
                data=[]
            )

        formatted = []

        for row in prices:

            formatted.append(
                {
                    "date": str(
                        row["price_date"]
                    ),

                    "open": float(
                        row["open_price"]
                    ),

                    "high": float(
                        row["high_price"]
                    ),

                    "low": float(
                        row["low_price"]
                    ),

                    "close": float(
                        row["close_price"]
                    ),

                    "volume": int(
                        row["volume"]
                    ),

                    "adj_close": (
                        float(row["adj_close"])
                        if row.get("adj_close")
                        else None
                    ),
                }
            )

        return self._result(
            success=True,
            message=(
                f"Loaded {len(formatted)} "
                f"price records for {symbol}."
            ),
            data=formatted,
            count=len(formatted)
        )

    # ─────────────────────────────────────────────────────────────
    # Price Change
    # ─────────────────────────────────────────────────────────────

    def get_price_change(
        self,
        symbol: str
    ) -> dict:
        """
        Returns today's price change for the stock card display.

        Reads from database — no API call.
        """

        change = self.service.get_price_change(symbol)

        return self._result(
            success=True,
            message="",
            data=change
        )

    # ─────────────────────────────────────────────────────────────
    # All Stocks
    # ─────────────────────────────────────────────────────────────

    def get_all_stocks(self) -> dict:
        """Returns all stocks in the database."""

        stocks = self.service.get_all_stocks()

        data = [
            stock.to_dict()
            for stock in stocks
        ]

        return self._result(
            success=True,
            message=f"{len(data)} stocks available.",
            data=data,
            count=len(data)
        )

    # ─────────────────────────────────────────────────────────────
    # Sectors
    # ─────────────────────────────────────────────────────────────

    def get_sectors(self) -> dict:
        """Returns all sectors for filter dropdowns."""

        sectors = self.service.get_sectors()

        return self._result(
            success=True,
            message=f"{len(sectors)} sectors found.",
            data=sectors
        )

    # ─────────────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _result(
        success: bool,
        message: str = "",
        data=None,
        count: int = 0
    ) -> dict:
        """
        Builds a standard result dictionary.

        Every controller method returns this exact shape
        so the GUI never needs to handle different formats.
        """

        return {
            "success": success,
            "message": message,
            "data": data,
            "count": count,
        }