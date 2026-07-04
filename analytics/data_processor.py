"""
analytics/data_processor.py
=============================
Loads price data from MySQL, cleans it, and
runs all technical indicator calculations.

This is the bridge between raw database data
and analysis-ready DataFrames.
"""

import logging
import pandas as pd
import numpy as np
from analytics.technical_indicators import TechnicalIndicators
from repositories.stock_repository import StockRepository

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Loads, cleans, and enriches stock price data.

    TYPICAL WORKFLOW:
        processor = DataProcessor()
        df = processor.load_price_data('AAPL')
        df = processor.calculate_all_indicators(df)
        # df now has 20+ columns of enriched data
    """

    def __init__(self, stock_repository: StockRepository = None):
        self.stock_repo = stock_repository or StockRepository()

    def load_price_data(self, symbol: str,
                        period_days: int = 365) -> pd.DataFrame:
        """
        Loads historical prices from MySQL into a clean DataFrame.

        WHY CONVERT TO DATAFRAME HERE?
            The repository returns a list of dicts — efficient for
            storage but awkward for mathematical operations.
            Pandas DataFrames are designed for exactly this:
            vectorised math on columns of numbers.

        Args:
            symbol:      Stock ticker
            period_days: Days of history to load

        Returns:
            Clean DataFrame with columns:
            date, open, high, low, close, volume, adj_close
        """
        stock = self.stock_repo.find_by_symbol(symbol)
        if not stock:
            logger.warning(f"Stock not found: {symbol}")
            return pd.DataFrame()

        from datetime import datetime, timedelta
        end_date   = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=period_days)
                      ).strftime('%Y-%m-%d')

        rows = self.stock_repo.get_historical_prices(
            stock.id, start_date, end_date
        )

        if not rows:
            logger.warning(f"No price data found for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df = self._clean_price_data(df)

        logger.info(f"Loaded {len(df)} rows for {symbol}")
        return df

    def _clean_price_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans raw price data from the database.

        CLEANING STEPS:
            1. Parse dates properly
            2. Convert price columns to float
            3. Sort by date ascending
            4. Remove duplicate dates
            5. Handle missing values
            6. Remove obviously wrong data (negative prices)

        WHY CLEAN DATA?
            Garbage in = garbage out.
            A single missing value can break an entire
            indicator calculation if not handled.
        """
        if df.empty:
            return df

        # ── Step 1: Parse dates ──────────────────────────────
        df['date'] = pd.to_datetime(df['price_date'])
        df = df.drop(columns=['price_date'], errors='ignore')

        # ── Step 2: Rename columns for consistency ───────────
        rename_map = {
            'open_price':  'open',
            'high_price':  'high',
            'low_price':   'low',
            'close_price': 'close',
        }
        df = df.rename(columns=rename_map)

        # ── Step 3: Convert to numeric ───────────────────────
        price_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in price_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # ── Step 4: Sort by date ascending ───────────────────
        df = df.sort_values('date').reset_index(drop=True)

        # ── Step 5: Remove duplicate dates ───────────────────
        dupes = df.duplicated(subset=['date'], keep='last')
        if dupes.any():
            logger.warning(f"Removed {dupes.sum()} duplicate date rows")
            df = df[~dupes].reset_index(drop=True)

        # ── Step 6: Remove invalid prices ────────────────────
        invalid = (
            (df['close'] <= 0) |
            (df['high']  <  df['low']) |
            df['close'].isna()
        )
        if invalid.any():
            logger.warning(f"Removed {invalid.sum()} invalid price rows")
            df = df[~invalid].reset_index(drop=True)

        # ── Step 7: Forward-fill small gaps ──────────────────
        # Weekend/holiday gaps are normal — don't fill those.
        # But if a single day has NaN open/high/low, use close.
        df['open']  = df['open'].fillna(df['close'])
        df['high']  = df['high'].fillna(df['close'])
        df['low']   = df['low'].fillna(df['close'])
        df['volume']= df['volume'].fillna(0).astype(int)

        # Set date as index for time-series operations
        df = df.set_index('date')

        logger.debug(f"Cleaned data shape: {df.shape}")
        return df

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates all technical indicators and adds them
        as new columns to the DataFrame.

        After this method, the DataFrame has 25+ columns
        covering every indicator we need for analysis and charts.

        Args:
            df: Clean price DataFrame from load_price_data()

        Returns:
            Enriched DataFrame with indicator columns added
        """
        if df.empty or len(df) < 20:
            logger.warning("Not enough data to calculate indicators (need 20+ rows)")
            return df

        ti = TechnicalIndicators

        # ── Moving Averages ──────────────────────────────────
        df['sma_20']  = ti.sma(df['close'], 20)
        df['sma_50']  = ti.sma(df['close'], 50)
        df['sma_200'] = ti.sma(df['close'], 200)
        df['ema_12']  = ti.ema(df['close'], 12)
        df['ema_26']  = ti.ema(df['close'], 26)

        # ── RSI ──────────────────────────────────────────────
        df['rsi_14'] = ti.rsi(df['close'], 14)

        # ── MACD ─────────────────────────────────────────────
        macd_df        = ti.macd(df['close'])
        df['macd']     = macd_df['macd']
        df['macd_signal'] = macd_df['signal']
        df['macd_hist']   = macd_df['histogram']

        # ── Bollinger Bands ──────────────────────────────────
        bb_df          = ti.bollinger_bands(df['close'])
        df['bb_upper'] = bb_df['upper']
        df['bb_middle']= bb_df['middle']
        df['bb_lower'] = bb_df['lower']
        df['bb_width'] = bb_df['bandwidth']

        # ── ATR ──────────────────────────────────────────────
        df['atr_14'] = ti.atr(df, 14)

        # ── VWAP ─────────────────────────────────────────────
        df['vwap'] = ti.vwap(df)

        # ── Returns and Volatility ───────────────────────────
        df['daily_return']      = ti.daily_returns(df['close'])
        df['cumulative_return'] = ti.cumulative_returns(df['close'])
        df['volatility_21']     = ti.volatility(df['close'], 21)

        # ── Price Position ───────────────────────────────────
        # Where is today's price relative to 52-week range?
        rolling_high = df['close'].rolling(252).max()
        rolling_low  = df['close'].rolling(252).min()
        df['pct_from_52w_high'] = (
            (df['close'] - rolling_high) / rolling_high * 100
        )
        df['pct_from_52w_low']  = (
            (df['close'] - rolling_low)  / rolling_low  * 100
        )

        # ── Signals ──────────────────────────────────────────
        df['ma_signal']  = ti.moving_average_crossover(df['close'])
        df['rsi_signal'] = ti.rsi_signals(df['rsi_14'])

        logger.info(
            f"Calculated {len([c for c in df.columns if c not in ['open','high','low','close','volume','adj_close']])} "
            f"indicator columns"
        )
        return df

    def get_latest_indicators(self, df: pd.DataFrame) -> dict:
        """
        Extracts the most recent row of indicators as a dict.
        Used by the GUI to display current indicator values.

        Returns:
            Dict of latest indicator values, all NaN replaced with None.
        """
        if df.empty:
            return {}

        latest = df.iloc[-1].copy()

        # Replace NaN with None for clean JSON/display
        result = {}
        for col, val in latest.items():
            if pd.isna(val):
                result[col] = None
            elif isinstance(val, (np.integer,)):
                result[col] = int(val)
            elif isinstance(val, (np.floating,)):
                result[col] = round(float(val), 4)
            else:
                result[col] = val

        return result

    def get_summary_stats(self, df: pd.DataFrame) -> dict:
        """
        Calculates summary statistics for a stock.
        Used on the stock detail page in the GUI.
        """
        if df.empty:
            return {}

        close = df['close']

        return {
            'current_price':    round(float(close.iloc[-1]), 2),
            'prev_close':       round(float(close.iloc[-2]), 2)
                                if len(close) > 1 else None,
            'day_change':       round(float(close.iloc[-1] - close.iloc[-2]), 2)
                                if len(close) > 1 else None,
            'day_change_pct':   round(float(
                                    (close.iloc[-1] - close.iloc[-2])
                                    / close.iloc[-2] * 100
                                ), 2) if len(close) > 1 else None,
            '52w_high':         round(float(close.max()), 2),
            '52w_low':          round(float(close.min()), 2),
            'avg_volume':       int(df['volume'].mean()),
            'total_return_pct': round(float(
                                    (close.iloc[-1] - close.iloc[0])
                                    / close.iloc[0] * 100
                                ), 2),
            'avg_volatility':   round(float(
                                    df['volatility_21'].mean()
                                ), 4) if 'volatility_21' in df.columns else None,
        }
