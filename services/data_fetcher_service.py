"""
services/data_fetcher_service.py
=================================
Orchestrates fetching stock data from APIs and saving to MySQL.

THIS IS THE MOST IMPORTANT SERVICE IN PHASE 6.

It follows this exact flow for every fetch:
    1. Check cache — return immediately if fresh data exists
    2. Call Yahoo Finance API
    3. Save raw data to MySQL
    4. Save to cache
    5. Return data to caller

WHY THIS LAYER EXISTS:
    The controller shouldn't know which API to call.
    The repository shouldn't know about caching.
    This service coordinates both.
"""

import logging
from typing import Optional
from models.stock import Stock
from api.yahoo_finance_api import YahooFinanceAPI
from api.cache_service import CacheService
from repositories.stock_repository import StockRepository
from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class DataFetcherService:
    """
    Fetches data from external APIs and persists it to MySQL.
    Uses caching to minimise API calls.
    """

    # Cache durations for different data types
    # Stock info changes rarely — cache for 1 hour
    STOCK_INFO_TTL    = 60
    # Prices during market hours — cache for 15 minutes
    PRICE_HISTORY_TTL = 15
    # Current quotes — cache for 5 minutes
    QUOTE_TTL         = 5

    def __init__(self):
        self.yahoo_api    = YahooFinanceAPI()
        self.cache        = CacheService()
        self.stock_repo   = StockRepository()

    def fetch_and_save_stock(self, symbol: str) -> Optional[Stock]:
        """
        Fetches stock info from Yahoo Finance and saves to MySQL.

        If the stock already exists in the database, updates it.
        If it's new, inserts it.

        Args:
            symbol: Stock ticker e.g. 'TSLA'

        Returns:
            Stock model or None if fetch fails
        """
        symbol    = symbol.upper().strip()
        cache_key = f"stock_info_{symbol}"

        # Step 1 — Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached stock info for {symbol}")
            return Stock.from_dict(cached)

        # Step 2 — Fetch from API
        stock = self.yahoo_api.get_stock_info(symbol)
        if not stock:
            logger.warning(f"Could not fetch stock info for {symbol}")
            return None

        # Step 3 — Save to MySQL
        try:
            self.stock_repo.save(stock)
            # Reload from DB to get the assigned id
            stock = self.stock_repo.find_by_symbol(symbol)
            logger.info(f"Stock saved to database: {symbol}")
        except Exception as e:
            logger.error(f"Failed to save stock {symbol} to database: {e}")
            return None

        # Step 4 — Save to cache
        self.cache.set(cache_key, stock.to_dict(), self.STOCK_INFO_TTL)

        return stock

    def fetch_and_save_history(self, symbol: str,
                                period: str = '1y') -> bool:
        """
        Fetches historical prices and saves to MySQL.

        Args:
            symbol: Stock ticker e.g. 'AAPL'
            period: '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'

        Returns:
            True if data was fetched and saved, False otherwise
        """
        symbol    = symbol.upper().strip()
        cache_key = f"history_{symbol}_{period}"

        # Check cache — skip API call if recent
        if self.cache.get(cache_key):
            logger.info(f"Price history for {symbol} is fresh — skipping fetch")
            return True

        # Ensure stock exists in DB first
        stock = self.stock_repo.find_by_symbol(symbol)
        if not stock:
            logger.info(f"Stock {symbol} not in DB — fetching info first...")
            stock = self.fetch_and_save_stock(symbol)
            if not stock:
                return False

        # Fetch historical prices
        df = self.yahoo_api.get_historical_prices(symbol, period)
        if df is None:
            logger.warning(f"No historical data returned for {symbol}")
            return False

        # Convert DataFrame to list of dicts
        price_dicts = self.yahoo_api.convert_df_to_price_dicts(df)
        if not price_dicts:
            return False

        # Save to MySQL
        try:
            saved = self.stock_repo.save_historical_prices(
                stock.id, price_dicts
            )
            logger.info(f"Saved {saved} price records for {symbol}")
        except Exception as e:
            logger.error(f"Failed to save prices for {symbol}: {e}")
            return False

        # Mark as cached so we don't refetch immediately
        self.cache.set(cache_key, {'fetched': True}, self.PRICE_HISTORY_TTL)
        return True

    def get_current_quotes(self, symbols: list[str]) -> dict:
        """
        Returns current prices for multiple stocks.
        Uses cache to avoid hammering the API.

        Args:
            symbols: List of tickers e.g. ['AAPL', 'MSFT', 'TSLA']

        Returns:
            Dict mapping symbol to price e.g. {'AAPL': 189.50}
        """
        if not symbols:
            return {}

        prices       = {}
        need_refresh = []

        # Check cache for each symbol
        for symbol in symbols:
            cache_key = f"quote_{symbol.upper()}"
            cached    = self.cache.get(cache_key)
            if cached:
                prices[symbol.upper()] = cached['price']
            else:
                need_refresh.append(symbol)

        # Fetch uncached symbols from API
        if need_refresh:
            logger.info(
                f"Fetching live quotes for: {', '.join(need_refresh)}"
            )
            fresh = self.yahoo_api.get_multiple_quotes(need_refresh)
            for symbol, price in fresh.items():
                prices[symbol] = price
                self.cache.set(
                    f"quote_{symbol}",
                    {'price': price},
                    self.QUOTE_TTL
                )

        return prices

    def fetch_watchlist_data(self, symbols: list[str]) -> dict:
        """
        Fetches and saves data for all stocks in a watchlist.
        Used when the app starts up to preload watchlist data.

        Returns dict of symbol → current price
        """
        logger.info(f"Preloading data for {len(symbols)} watchlist stocks...")

        for symbol in symbols:
            # Fetch info if not already in DB
            stock = self.stock_repo.find_by_symbol(symbol)
            if not stock:
                self.fetch_and_save_stock(symbol)

            # Fetch 1 year of history if not cached
            self.fetch_and_save_history(symbol, '1y')

        # Return current quotes for all
        return self.get_current_quotes(symbols)
