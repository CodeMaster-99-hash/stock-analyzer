"""
services/data_fetcher_service.py
=================================
Orchestrates fetching stock data from APIs and saving to MySQL.
Supports fetching ANY stock globally — not just hardcoded symbols.

Flow for every fetch:
    1. Check cache — return immediately if fresh data exists
    2. Call Yahoo Finance API
    3. Save to MySQL
    4. Save to cache
    5. Return data to caller
"""

import logging
from typing import Optional

from models.stock import Stock
from api.yahoo_finance_api import YahooFinanceAPI
from api.cache_service import CacheService
from repositories.stock_repository import StockRepository

logger = logging.getLogger(__name__)


class DataFetcherService:
    """
    Fetches data from external APIs and persists it to MySQL.

    Uses caching to minimise API calls and avoid rate limits.
    """

    # Cache durations in minutes
    STOCK_INFO_TTL = 60
    PRICE_HISTORY_TTL = 15
    QUOTE_TTL = 5

    def __init__(self):
        self.yahoo_api = YahooFinanceAPI()
        self.cache = CacheService()
        self.stock_repo = StockRepository()

    def fetch_and_save_stock(
        self,
        symbol: str
    ) -> Optional[Stock]:
        """
        Fetches stock information from Yahoo Finance and saves it
        to MySQL.

        Works for any globally traded symbol.

        Args:
            symbol: Yahoo Finance symbol.
                    Examples: AAPL, RELIANCE.NS, BTC-USD

        Returns:
            Stock model or None if fetching fails.
        """

        symbol = symbol.upper().strip()
        cache_key = f"stock_info_{symbol}"

        # Step 1: Check cache
        cached = self.cache.get(cache_key)

        if cached:
            logger.info(
                f"Returning cached stock info for {symbol}"
            )
            return Stock.from_dict(cached)

        # Step 2: Fetch from Yahoo Finance
        stock = self.yahoo_api.get_stock_info(symbol)

        if not stock:
            logger.warning(
                f"Could not fetch stock info for {symbol}"
            )
            return None

        # Step 3: Save to MySQL
        try:
            self.stock_repo.save(stock)

            # Reload from DB to get assigned ID
            stock = self.stock_repo.find_by_symbol(symbol)

            if not stock:
                logger.error(
                    f"Stock {symbol} was saved but could not "
                    f"be retrieved from database."
                )
                return None

            logger.info(
                f"Stock saved to database: {symbol}"
            )

        except Exception as e:
            logger.error(
                f"Failed to save stock {symbol} to database: {e}"
            )
            return None

        # Step 4: Save to cache
        self.cache.set(
            cache_key,
            stock.to_dict(),
            self.STOCK_INFO_TTL
        )

        return stock

    def fetch_and_save_history(
        self,
        symbol: str,
        period: str = "1y"
    ) -> bool:
        """
        Fetches historical prices and saves them to MySQL.

        Args:
            symbol: Yahoo Finance symbol.
            period: 1mo, 3mo, 6mo, 1y, 2y, 5y, max.

        Returns:
            True if successful, otherwise False.
        """

        symbol = symbol.upper().strip()
        cache_key = f"history_{symbol}_{period}"

        # Check cache
        if self.cache.get(cache_key):
            logger.info(
                f"Price history for {symbol} is fresh. "
                f"Skipping API request."
            )
            return True

        # Ensure stock exists in database
        stock = self.stock_repo.find_by_symbol(symbol)

        if not stock:
            logger.info(
                f"Stock {symbol} not in DB. "
                f"Fetching stock information first..."
            )

            stock = self.fetch_and_save_stock(symbol)

            if not stock:
                return False

        # Fetch historical prices
        df = self.yahoo_api.get_historical_prices(
            symbol,
            period
        )

        if df is None or df.empty:
            logger.warning(
                f"No historical data returned for {symbol}"
            )
            return False

        # Convert DataFrame to dictionaries
        price_dicts = (
            self.yahoo_api.convert_df_to_price_dicts(df)
        )

        if not price_dicts:
            logger.warning(
                f"No valid price records found for {symbol}"
            )
            return False

        # Save historical prices
        try:
            saved = self.stock_repo.save_historical_prices(
                stock.id,
                price_dicts
            )

            logger.info(
                f"Saved {saved} price records for {symbol}"
            )

        except Exception as e:
            logger.error(
                f"Failed to save prices for {symbol}: {e}"
            )
            return False

        # Mark history as cached
        self.cache.set(
            cache_key,
            {"fetched": True},
            self.PRICE_HISTORY_TTL
        )

        return True

    def get_current_quotes(
        self,
        symbols: list[str]
    ) -> dict:
        """
        Returns current prices for multiple stocks.

        Uses cache to avoid unnecessary API calls.

        Args:
            symbols: List of ticker symbols.

        Returns:
            Dictionary mapping symbols to prices.

            Example:
                {
                    "AAPL": 189.50,
                    "MSFT": 420.10
                }
        """

        if not symbols:
            return {}

        prices = {}
        need_refresh = []

        # Check cache for each symbol
        for symbol in symbols:

            symbol = symbol.upper()
            cache_key = f"quote_{symbol}"

            cached = self.cache.get(cache_key)

            if cached:
                prices[symbol] = cached["price"]
            else:
                need_refresh.append(symbol)

        # Fetch uncached symbols
        if need_refresh:

            logger.info(
                "Fetching live quotes for: "
                + ", ".join(need_refresh)
            )

            fresh_prices = (
                self.yahoo_api.get_multiple_quotes(
                    need_refresh
                )
            )

            for symbol, price in fresh_prices.items():

                symbol = symbol.upper()
                prices[symbol] = price

                self.cache.set(
                    f"quote_{symbol}",
                    {"price": price},
                    self.QUOTE_TTL
                )

        return prices

    def fetch_any_stock(
        self,
        symbol: str
    ) -> dict:
        """
        Fetches ANY stock/asset from Yahoo Finance.

        Saves stock information and one year of historical
        price data to MySQL.

        Supported examples:

            US:
                AAPL
                TSLA
                NVDA

            India:
                RELIANCE.NS
                TCS.NS
                INFY.NS

            UK:
                TSCO.L
                HSBA.L

            Crypto:
                BTC-USD
                ETH-USD
                SOL-USD

            ETFs:
                SPY
                QQQ
                GLD

        Returns:
            Dictionary containing operation status and data.
        """

        symbol = symbol.upper().strip()

        if not symbol:
            return {
                "success": False,
                "message": "Stock symbol cannot be empty.",
                "symbol": ""
            }

        logger.info(
            f"Fetching any stock: {symbol}"
        )

        # Step 1: Fetch and save stock information
        stock = self.fetch_and_save_stock(symbol)

        if not stock:
            return {
                "success": False,
                "message": (
                    f"Could not find '{symbol}' on "
                    f"Yahoo Finance. "
                    f"Please check the symbol and try again."
                ),
                "symbol": symbol
            }

        # Step 2: Fetch and save one year of history
        history_ok = self.fetch_and_save_history(
            symbol,
            "1y"
        )

        # Step 3: Get current price
        price = (
            self.yahoo_api.get_current_price_simple(
                symbol
            )
        )

        logger.info(
            f"fetch_any_stock('{symbol}') complete - "
            f"price={price}, history={history_ok}"
        )

        return {
            "success": True,
            "message": (
                f"Successfully loaded {stock.name}"
            ),
            "symbol": symbol,
            "name": stock.name,
            "sector": stock.sector or "",
            "exchange": stock.exchange or "",
            "price": price,
            "history_ok": history_ok
        }

    def fetch_watchlist_data(
        self,
        symbols: list[str]
    ) -> dict:
        """
        Fetches and saves data for all stocks in a watchlist.

        Used when the application starts to preload
        watchlist data.

        Returns:
            Dictionary mapping symbols to current prices.
        """

        logger.info(
            f"Preloading data for "
            f"{len(symbols)} watchlist stocks..."
        )

        for symbol in symbols:

            symbol = symbol.upper().strip()

            # Ensure stock exists
            stock = self.stock_repo.find_by_symbol(
                symbol
            )

            if not stock:
                self.fetch_and_save_stock(symbol)

            # Ensure historical data exists
            self.fetch_and_save_history(
                symbol,
                "1y"
            )

        # Return current prices
        return self.get_current_quotes(symbols)