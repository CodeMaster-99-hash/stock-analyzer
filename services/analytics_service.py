"""
services/analytics_service.py
===============================
Orchestrates data processing and saves
calculated indicators back to MySQL.
"""

import logging
import time
import pandas as pd
from analytics.data_processor import DataProcessor
from repositories.stock_repository import StockRepository
from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class AnalyticsService:

    # In-memory cache: {(symbol, period_days): (timestamp, dataframe)}
    _cache = {}
    _cache_ttl_seconds = 60   # Recalculate at most once per minute

    def __init__(self, stock_repository: StockRepository = None):
        self.stock_repo = stock_repository or StockRepository()
        self.processor  = DataProcessor(self.stock_repo)

    def get_enriched_data(self, symbol: str,
                           period_days: int = 365) -> pd.DataFrame:
        """
        Returns a fully enriched DataFrame for a stock.
        Uses a short-lived in-memory cache to avoid recalculating
        the same indicators repeatedly within a few seconds —
        e.g. dashboard, charts, and predictions all requesting
        the same symbol in quick succession.
        """
        cache_key = (symbol.upper(), period_days)
        now = time.time()

        if cache_key in self._cache:
            cached_time, cached_df = self._cache[cache_key]
            if now - cached_time < self._cache_ttl_seconds:
                logger.debug(f"In-memory cache HIT for {symbol}")
                return cached_df.copy()

        df = self.processor.load_price_data(symbol, period_days)

        if df.empty:
            logger.warning(f"No data to process for {symbol}")
            return df

        df = self.processor.calculate_all_indicators(df)
        self._cache[cache_key] = (now, df)

        logger.info(f"Enriched data ready for {symbol}: {df.shape}")
        return df    
    def get_latest_indicators(self, symbol: str) -> dict:
        """
        Returns the most recent indicator values for a stock.
        Used by the GUI to populate the indicators panel.
        """
        df = self.get_enriched_data(symbol, period_days=365)
        if df.empty:
            return {}
        return self.processor.get_latest_indicators(df)

    def get_summary(self, symbol: str) -> dict:
        """
        Returns summary statistics for a stock.
        """
        df = self.get_enriched_data(symbol, period_days=365)
        if df.empty:
            return {}
        return self.processor.get_summary_stats(df)

    def save_indicators_to_db(self, symbol: str) -> bool:
        """
        Calculates and saves technical indicators to the
        technical_indicators table in MySQL.

        WHY SAVE TO DB?
            Calculating indicators takes time.
            By saving to MySQL, the GUI can load pre-calculated
            values instantly instead of recalculating each time.
        """
        stock = self.stock_repo.find_by_symbol(symbol)
        if not stock:
            logger.warning(f"Cannot save indicators — stock not found: {symbol}")
            return False

        df = self.get_enriched_data(symbol, period_days=730)
        if df.empty:
            return False

        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor()

            rows_saved = 0
            for date, row in df.iterrows():
                def safe(val):
                    """Convert NaN to None for MySQL."""
                    if pd.isna(val):
                        return None
                    return round(float(val), 6)

                cursor.execute(
                    """INSERT INTO technical_indicators
                       (stock_id, calc_date, rsi_14, macd, macd_signal,
                        macd_hist, bb_upper, bb_middle, bb_lower,
                        sma_20, sma_50, sma_200, ema_12, ema_26,
                        vwap, atr_14)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE
                           rsi_14     = VALUES(rsi_14),
                           macd       = VALUES(macd),
                           macd_signal= VALUES(macd_signal),
                           macd_hist  = VALUES(macd_hist),
                           bb_upper   = VALUES(bb_upper),
                           bb_middle  = VALUES(bb_middle),
                           bb_lower   = VALUES(bb_lower),
                           sma_20     = VALUES(sma_20),
                           sma_50     = VALUES(sma_50),
                           sma_200    = VALUES(sma_200),
                           ema_12     = VALUES(ema_12),
                           ema_26     = VALUES(ema_26),
                           vwap       = VALUES(vwap),
                           atr_14     = VALUES(atr_14)""",
                    (
                        stock.id,
                        date.strftime('%Y-%m-%d'),
                        safe(row.get('rsi_14')),
                        safe(row.get('macd')),
                        safe(row.get('macd_signal')),
                        safe(row.get('macd_hist')),
                        safe(row.get('bb_upper')),
                        safe(row.get('bb_middle')),
                        safe(row.get('bb_lower')),
                        safe(row.get('sma_20')),
                        safe(row.get('sma_50')),
                        safe(row.get('sma_200')),
                        safe(row.get('ema_12')),
                        safe(row.get('ema_26')),
                        safe(row.get('vwap')),
                        safe(row.get('atr_14')),
                    )
                )
                rows_saved += 1

            conn.commit()
            cursor.close()
            logger.info(
                f"Saved {rows_saved} indicator rows for {symbol}"
            )
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save indicators for {symbol}: {e}")
            return False
        finally:
            conn.close()

    def compare_stocks(self, symbols: list[str],
                        period_days: int = 365) -> dict:
        """
        Compares multiple stocks side by side.
        Returns normalised cumulative returns for chart overlay.

        WHY NORMALISE?
            AAPL at $189 and MSFT at $415 can't be directly compared.
            Normalising to percentage return since day 1 puts them
            on the same scale — who grew more, not who costs more.
        """
        comparison = {}

        for symbol in symbols:
            df = self.get_enriched_data(symbol, period_days)
            if df.empty:
                continue

            comparison[symbol] = {
                'dates':              [str(d.date()) for d in df.index],
                'close':              df['close'].round(2).tolist(),
                'cumulative_return':  (
                    df['cumulative_return'] * 100
                ).round(2).tolist(),
                'volatility':         df['volatility_21'].round(4).tolist(),
                'latest_indicators':  self.processor.get_latest_indicators(df),
                'summary':            self.processor.get_summary_stats(df),
            }

        return comparison
