"""
repositories/stock_repository.py
=================================
All database operations for stocks and historical prices.

WHY %s PLACEHOLDERS INSTEAD OF f-STRINGS?
    NEVER do this:
        query = f"SELECT * FROM stocks WHERE symbol = '{symbol}'"

    If symbol = "'; DROP TABLE stocks; --"
    your query becomes:
        SELECT * FROM stocks WHERE symbol = ''; DROP TABLE stocks; --'

    This is called SQL Injection — the most common web vulnerability.

    Always use parameterized queries:
        query = "SELECT * FROM stocks WHERE symbol = %s"
        cursor.execute(query, (symbol,))

    MySQL substitutes the value safely, treating it as data only,
    never as SQL code. The attack above becomes harmless.
"""

import logging
from typing import Optional
from models.stock import Stock
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class StockRepository(BaseRepository):
    """Handles all database operations for the stocks table."""

    def find_all(self) -> list[Stock]:
        """
        Returns every active stock in the database.
        Used to populate the stock search dropdown.
        """
        rows = self._execute_query(
            "SELECT * FROM stocks WHERE is_active = TRUE ORDER BY symbol"
        )
        return [Stock.from_dict(row) for row in rows]

    def find_by_symbol(self, symbol: str) -> Optional[Stock]:
        """
        Returns a single stock by its ticker symbol.
        Returns None if not found — never raises an exception for missing data.

        WHY RETURN None INSTEAD OF RAISING AN EXCEPTION?
            Not finding a stock is a normal situation, not an error.
            Exceptions are for unexpected failures (network down, DB offline).
            The caller can simply check: if stock is None: handle it.
        """
        rows = self._execute_query(
            "SELECT * FROM stocks WHERE symbol = %s AND is_active = TRUE",
            (symbol.upper(),)
        )
        return Stock.from_dict(rows[0]) if rows else None

    def find_by_sector(self, sector: str) -> list[Stock]:
        """Returns all stocks in a given sector."""
        rows = self._execute_query(
            "SELECT * FROM stocks WHERE sector = %s AND is_active = TRUE ORDER BY symbol",
            (sector,)
        )
        return [Stock.from_dict(row) for row in rows]

    def search(self, query: str) -> list[Stock]:
        """
        Searches stocks by symbol or name.
        The % characters are SQL wildcards — matches anything before/after.

        Example: search('app') matches 'AAPL', 'Apple Inc.'
        """
        pattern = f"%{query.upper()}%"
        rows = self._execute_query(
            """SELECT * FROM stocks
               WHERE (UPPER(symbol) LIKE %s OR UPPER(name) LIKE %s)
               AND is_active = TRUE
               ORDER BY symbol
               LIMIT 20""",
            (pattern, pattern)
        )
        return [Stock.from_dict(row) for row in rows]

    def save(self, stock: Stock) -> int:
        """
        Inserts a new stock or updates it if the symbol already exists.

        INSERT ... ON DUPLICATE KEY UPDATE is MySQL's upsert.
        If the symbol (unique key) already exists, it updates instead
        of failing. This is safe to call repeatedly.
        """
        return self._execute_write(
            """INSERT INTO stocks
               (symbol, name, sector, industry, exchange, country,
                currency, market_cap, pe_ratio, dividend_yield,
                week_52_high, week_52_low, description, last_updated)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
               ON DUPLICATE KEY UPDATE
                name           = VALUES(name),
                sector         = VALUES(sector),
                industry       = VALUES(industry),
                market_cap     = VALUES(market_cap),
                pe_ratio       = VALUES(pe_ratio),
                dividend_yield = VALUES(dividend_yield),
                week_52_high   = VALUES(week_52_high),
                week_52_low    = VALUES(week_52_low),
                description    = VALUES(description),
                last_updated   = NOW()""",
            (
                stock.symbol, stock.name, stock.sector, stock.industry,
                stock.exchange, stock.country, stock.currency,
                stock.market_cap, stock.pe_ratio, stock.dividend_yield,
                stock.week_52_high, stock.week_52_low, stock.description
            )
        )

    def save_historical_prices(self, stock_id: int, prices: list[dict]) -> int:
        """
        Bulk inserts historical OHLCV price data.
        Uses executemany for performance — one round trip to MySQL
        instead of thousands of individual inserts.

        Args:
            stock_id: The stock's database ID
            prices:   List of dicts with keys:
                      date, open, high, low, close, adj_close, volume
        """
        params_list = [
            (
                stock_id,
                row['date'],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row.get('adj_close'),
                row.get('volume', 0),
            )
            for row in prices
        ]
        return self._execute_many(
            """INSERT IGNORE INTO historical_prices
               (stock_id, price_date, open_price, high_price,
                low_price, close_price, adj_close, volume)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            params_list
        )

    def get_historical_prices(self, stock_id: int,
                               start_date: str = None,
                               end_date: str = None) -> list[dict]:
        """
        Returns historical prices for a stock within a date range.

        Args:
            stock_id:   The stock's database ID
            start_date: 'YYYY-MM-DD' string or None for all history
            end_date:   'YYYY-MM-DD' string or None for today
        """
        if start_date and end_date:
            return self._execute_query(
                """SELECT * FROM historical_prices
                   WHERE stock_id = %s
                   AND price_date BETWEEN %s AND %s
                   ORDER BY price_date ASC""",
                (stock_id, start_date, end_date)
            )
        elif start_date:
            return self._execute_query(
                """SELECT * FROM historical_prices
                   WHERE stock_id = %s AND price_date >= %s
                   ORDER BY price_date ASC""",
                (stock_id, start_date)
            )
        else:
            return self._execute_query(
                """SELECT * FROM historical_prices
                   WHERE stock_id = %s
                   ORDER BY price_date ASC""",
                (stock_id,)
            )

    def get_latest_price(self, stock_id: int) -> Optional[dict]:
        """Returns the most recent price row for a stock."""
        rows = self._execute_query(
            """SELECT * FROM historical_prices
               WHERE stock_id = %s
               ORDER BY price_date DESC
               LIMIT 1""",
            (stock_id,)
        )
        return rows[0] if rows else None

    def get_all_sectors(self) -> list[str]:
        """Returns a distinct list of sectors for filter dropdowns."""
        rows = self._execute_query(
            """SELECT DISTINCT sector FROM stocks
               WHERE sector IS NOT NULL
               ORDER BY sector"""
        )
        return [row['sector'] for row in rows]
