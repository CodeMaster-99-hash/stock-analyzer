"""
controllers/stock_controller.py
================================
Bridges the GUI and StockService.

CONTROLLER RESPONSIBILITIES:
    1. Receive calls from the GUI
    2. Validate and prepare inputs
    3. Call the appropriate service method
    4. Format the result for the GUI to display
    5. Handle errors so the GUI never crashes

The GUI should never need to know HOW data is fetched.
It just calls the controller and gets back a clean result.
"""

import logging
from typing import Optional
from services.stock_service import StockService

logger = logging.getLogger(__name__)


class StockController:
    """
    Handles all GUI interactions related to stocks.

    USAGE IN GUI (Phase 8):
        self.controller = StockController()

        # When search button is clicked:
        results = self.controller.search('AAPL')

        # When a stock is selected:
        data = self.controller.get_stock_detail('AAPL')
    """

    def __init__(self, stock_service: StockService = None):
        self.service = stock_service or StockService()

    def search(self, query: str) -> dict:
        """
        Handles stock search from the GUI search bar.

        Returns a result dict — the GUI reads this and
        decides what to display. The GUI never handles
        exceptions directly.

        Returns:
            {
                'success': True/False,
                'data':    list of stock dicts,
                'message': human-readable status message,
                'count':   number of results
            }
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

        stocks  = self.service.search_stocks(query)
        data    = [s.to_dict() for s in stocks]

        if not data:
            return self._result(
                success=False,
                message=f"No stocks found matching '{query}'.",
                data=[]
            )

        return self._result(
            success=True,
            message=f"Found {len(data)} result(s) for '{query}'.",
            data=data,
            count=len(data)
        )

    def get_stock_detail(self, symbol: str) -> dict:
        """
        Returns full details for a single stock.
        Called when user clicks on a stock to view it.
        """
        symbol = symbol.upper().strip()

        if not symbol:
            return self._result(success=False, message="No symbol provided.")

        stock = self.service.get_stock(symbol)

        if not stock:
            return self._result(
                success=False,
                message=f"{symbol} was not found in the database. "
                        f"Try fetching it from the API first."
            )

        return self._result(
            success=True,
            message=f"Loaded {symbol}.",
            data=stock.to_dict()
        )

    def get_price_history(self, symbol: str, period_days: int = 365) -> dict:
        """
        Returns historical price data formatted for charting.
        The chart widget in Phase 8 will consume this directly.

        Args:
            symbol:      Stock ticker
            period_days: Number of days of history (30, 90, 180, 365)
        """
        valid_periods = {30, 90, 180, 365, 730, 1825}
        if period_days not in valid_periods:
            period_days = 365

        prices = self.service.get_price_history(symbol, period_days)

        if not prices:
            return self._result(
                success=False,
                message=f"No price history found for {symbol}. "
                        f"Fetch data from API first.",
                data=[]
            )

        # Format dates as strings for the chart widget
        formatted = []
        for row in prices:
            formatted.append({
                'date':        str(row['price_date']),
                'open':        float(row['open_price']),
                'high':        float(row['high_price']),
                'low':         float(row['low_price']),
                'close':       float(row['close_price']),
                'volume':      int(row['volume']),
                'adj_close':   float(row['adj_close']) if row.get('adj_close') else None,
            })

        return self._result(
            success=True,
            message=f"Loaded {len(formatted)} price records for {symbol}.",
            data=formatted,
            count=len(formatted)
        )

    def get_price_change(self, symbol: str) -> dict:
        """
        Returns today's price change for display in the GUI.
        Used to show the green/red price change on stock cards.
        """
        change = self.service.get_price_change(symbol)
        return self._result(
            success=True,
            message="",
            data=change
        )

    def get_all_stocks(self) -> dict:
        """
        Returns all stocks for populating dropdowns and lists.
        """
        stocks = self.service.get_all_stocks()
        data   = [s.to_dict() for s in stocks]
        return self._result(
            success=True,
            message=f"{len(data)} stocks available.",
            data=data,
            count=len(data)
        )

    def get_sectors(self) -> dict:
        """Returns all sectors for the sector filter dropdown."""
        sectors = self.service.get_sectors()
        return self._result(
            success=True,
            message=f"{len(sectors)} sectors found.",
            data=sectors
        )

    @staticmethod
    def _result(success: bool, message: str = "",
                data=None, count: int = 0) -> dict:
        """
        Builds a standard result dict.

        WHY A STANDARD FORMAT?
            Every controller method returns the same shape.
            The GUI checks result['success'] first, then reads
            result['data']. This consistency means the GUI
            never needs to handle different return formats.
        """
        return {
            'success': success,
            'message': message,
            'data':    data,
            'count':   count,
        }
