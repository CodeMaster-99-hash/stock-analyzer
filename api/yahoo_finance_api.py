"""
api/yahoo_finance_api.py
=========================
Fetches stock data from Yahoo Finance using yfinance.
Supports searching any stock globally by symbol or name.
"""

import time
import logging
import requests
import yfinance as yf
import pandas as pd
from typing import Optional

from models.stock import Stock


logger = logging.getLogger(__name__)


class YahooFinanceAPI:
    """Wrapper around the yfinance library."""

    def get_stock_info(self, symbol: str) -> Optional[Stock]:
        """Fetch company information. Uses fast_info as fallback."""

        symbol = symbol.upper().strip()
        logger.info(f"Fetching stock info for {symbol} from Yahoo Finance...")

        try:
            ticker = yf.Ticker(symbol)
            time.sleep(1)

            try:
                info = ticker.info or {}
            except Exception:
                info = {}

            # Fallback to fast_info
            if not info.get("longName"):
                try:
                    fast = ticker.fast_info

                    return Stock(
                        symbol=symbol,
                        name=symbol,
                        currency=getattr(fast, "currency", "USD"),
                        week_52_high=getattr(fast, "year_high", None),
                        week_52_low=getattr(fast, "year_low", None),
                        market_cap=getattr(fast, "market_cap", None),
                        exchange=getattr(fast, "exchange", None),
                    )

                except Exception as e:
                    logger.error(f"fast_info failed for {symbol}: {e}")
                    return None

            return Stock(
                symbol=symbol,
                name=(
                    info.get("longName")
                    or info.get("shortName")
                    or symbol
                ),
                sector=info.get("sector"),
                industry=info.get("industry"),
                exchange=info.get("exchange"),
                country=info.get("country"),
                currency=info.get("currency", "USD"),
                market_cap=info.get("marketCap"),
                pe_ratio=info.get("trailingPE"),
                dividend_yield=info.get("dividendYield"),
                week_52_high=info.get("fiftyTwoWeekHigh"),
                week_52_low=info.get("fiftyTwoWeekLow"),
                description=info.get("longBusinessSummary"),
            )

        except Exception as e:
            logger.error(f"Failed to fetch info for {symbol}: {e}")
            return None

    def get_historical_prices(
        self,
        symbol: str,
        period: str = "1y"
    ) -> Optional[pd.DataFrame]:
        """Fetch historical OHLCV price data using yf.download."""

        symbol = symbol.upper().strip()
        logger.info(f"Fetching {period} price history for {symbol}...")

        try:
            time.sleep(1)

            df = yf.download(
                tickers=symbol,
                period=period,
                interval="1d",
                progress=False,
                auto_adjust=False,
            )

            if df is None or df.empty:
                logger.warning(f"No price data returned for {symbol}")
                return None

            # Handle MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.reset_index()

            # Normalize column names
            df.columns = [
                c.lower().replace(" ", "_")
                for c in df.columns
            ]

            logger.info(
                f"Fetched {len(df)} price records for {symbol} "
                f"({df['date'].iloc[0]} to {df['date'].iloc[-1]})"
            )

            return df

        except Exception as e:
            logger.error(
                f"Failed to fetch price history for {symbol}: {e}"
            )
            return None

    def get_multiple_quotes(self, symbols: list[str]) -> dict:
        """
        Fetch current prices using fast_info per ticker.

        Most reliable method — avoids MultiIndex column issues.
        """

        if not symbols:
            return {}

        logger.info(
            f"Fetching quotes for {len(symbols)} symbols..."
        )

        prices = {}

        for symbol in symbols:
            symbol = symbol.upper()

            try:
                ticker = yf.Ticker(symbol)
                fast = ticker.fast_info

                price = getattr(
                    fast,
                    "last_price",
                    None
                )

                if price is None:
                    price = getattr(
                        fast,
                        "previous_close",
                        None
                    )

                if price is not None:
                    prices[symbol] = round(float(price), 2)
                else:
                    logger.warning(
                        f"No quote data for {symbol}"
                    )

                time.sleep(0.15)

            except Exception as e:
                logger.warning(
                    f"Failed to get quote for {symbol}: {e}"
                )

        logger.info(
            f"Retrieved quotes for {len(prices)} symbols."
        )

        return prices

    def get_current_price_simple(self, symbol: str) -> float:
        """
        Get current price for any symbol using fast_info.

        Works for:
        - Stocks
        - ETFs
        - Crypto (BTC-USD)
        - Forex
        """

        try:
            symbol = symbol.upper().strip()

            ticker = yf.Ticker(symbol)
            fast = ticker.fast_info

            price = getattr(
                fast,
                "last_price",
                None
            )

            if price is None:
                price = getattr(
                    fast,
                    "previous_close",
                    None
                )

            return round(float(price), 2) if price else 0.0

        except Exception as e:
            logger.warning(
                f"Price fetch failed for {symbol}: {e}"
            )
            return 0.0

    def search_symbols(self, query: str) -> list[dict]:
        """
        Search Yahoo Finance for stocks matching a query.

        Works for markets globally:

        US stocks:
            AAPL, MSFT, TSLA

        Indian stocks:
            RELIANCE.NS, TCS.NS

        Crypto:
            BTC-USD, ETH-USD

        ETFs:
            SPY, QQQ, VTI

        European:
            ASML.AS, SAP.DE

        Args:
            query: Search term such as 'Tesla', 'AAPL',
                   or 'Reliance'.

        Returns:
            List of dictionaries containing:
            symbol, name, exchange, and type.
        """

        if not query or len(query.strip()) < 1:
            return []

        query = query.strip()

        logger.info(
            f"Searching Yahoo Finance for: {query}"
        )

        try:
            time.sleep(0.5)

            url = (
                "https://query1.finance.yahoo.com/"
                "v1/finance/search"
            )

            params = {
                "q": query,
                "quotesCount": 20,
                "newsCount": 0,
                "enableFuzzyQuery": False,
                "quotesQueryId": "tss_match_phrase_query",
            }

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=10,
            )

            response.raise_for_status()

            data = response.json()

            results = []

            for quote in data.get("quotes", []):
                symbol = quote.get("symbol", "")

                name = (
                    quote.get("longname")
                    or quote.get("shortname", "")
                )

                exchange = quote.get(
                    "exchange",
                    ""
                )

                quote_type = quote.get(
                    "quoteType",
                    ""
                )

                # Include equities, ETFs, crypto,
                # currencies, futures, and indexes
                if quote_type not in (
                    "EQUITY",
                    "ETF",
                    "CRYPTOCURRENCY",
                    "CURRENCY",
                    "FUTURE",
                    "INDEX",
                ):
                    continue

                if not symbol or not name:
                    continue

                results.append(
                    {
                        "symbol": symbol,
                        "name": name,
                        "exchange": exchange,
                        "type": quote_type,
                    }
                )

            logger.info(
                f"Search '{query}' returned "
                f"{len(results)} results"
            )

            return results[:15]

        except Exception as e:
            logger.error(
                f"Symbol search failed for '{query}': {e}"
            )
            return []

    def convert_df_to_price_dicts(
        self,
        df: pd.DataFrame
    ) -> list[dict]:
        """Convert a yfinance DataFrame into a list of dictionaries."""

        if df is None or df.empty:
            return []

        price_list = []

        for _, row in df.iterrows():
            try:
                date = row["date"]

                if hasattr(date, "date"):
                    date = date.date()

                price_list.append(
                    {
                        "date": str(date),

                        "open": round(
                            float(row["open"]),
                            4
                        ),

                        "high": round(
                            float(row["high"]),
                            4
                        ),

                        "low": round(
                            float(row["low"]),
                            4
                        ),

                        "close": round(
                            float(row["close"]),
                            4
                        ),

                        "adj_close": (
                            round(
                                float(row["adj_close"]),
                                4
                            )
                            if (
                                "adj_close" in row
                                and pd.notna(
                                    row.get("adj_close")
                                )
                            )
                            else None
                        ),

                        "volume": (
                            int(row["volume"])
                            if pd.notna(
                                row.get("volume", 0)
                            )
                            else 0
                        ),
                    }
                )

            except Exception as e:
                logger.warning(
                    f"Skipping malformed price row: {e}"
                )
                continue

        return price_list