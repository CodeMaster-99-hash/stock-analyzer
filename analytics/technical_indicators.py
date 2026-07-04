"""
analytics/technical_indicators.py
===================================
Pure calculation functions for technical indicators.

WHY PURE FUNCTIONS?
    Each function takes a Pandas Series or DataFrame and
    returns a calculated Series. No database calls, no API
    calls, no side effects.

    This makes them:
    - Easy to test (input → output, nothing else)
    - Reusable anywhere in the app
    - Easy to understand in isolation

PANDAS REMINDER:
    A Series is a single column of data with an index.
    A DataFrame is multiple Series side by side.
    Most indicators operate on the 'close' price Series.
"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Collection of technical indicator calculations.
    All methods are static — no instance needed.

    Usage:
        df['sma_20'] = TechnicalIndicators.sma(df['close'], 20)
        df['rsi']    = TechnicalIndicators.rsi(df['close'])
    """

    # ──────────────────────────────────────────────────────────
    # MOVING AVERAGES
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """
        Simple Moving Average.

        Formula: Average of the last N closing prices.

        Example with period=3 and prices [10, 11, 12, 13, 14]:
            Day 3: (10+11+12) / 3 = 11.0
            Day 4: (11+12+13) / 3 = 12.0
            Day 5: (12+13+14) / 3 = 13.0

        The first (period-1) values are NaN because we don't
        have enough history yet. This is correct behaviour.

        Args:
            series: Pandas Series of prices (usually close)
            period: Number of periods to average

        Returns:
            Series of SMA values
        """
        return series.rolling(window=period, min_periods=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """
        Exponential Moving Average.

        Unlike SMA which weights all periods equally,
        EMA gives more weight to recent prices.

        The smoothing factor (alpha) = 2 / (period + 1)
        For a 12-period EMA: alpha = 2/13 = 0.154
        Each day: EMA = (close * alpha) + (prev_EMA * (1 - alpha))

        WHY EMA OVER SMA?
            EMA reacts faster to price changes.
            When a stock suddenly moves, EMA signals it sooner.
            SMA lags behind — it's still averaging old prices.
        """
        return series.ewm(
            span       = period,
            adjust     = False,
            min_periods= period
        ).mean()

    # ──────────────────────────────────────────────────────────
    # RSI — RELATIVE STRENGTH INDEX
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index (RSI).

        RSI measures momentum — how fast prices are moving
        up vs down. It oscillates between 0 and 100.

        INTERPRETATION:
            RSI > 70 → Overbought (price may reverse downward)
            RSI < 30 → Oversold  (price may reverse upward)
            RSI = 50 → Neutral

        FORMULA:
            1. Calculate daily price change: delta = close - prev_close
            2. Separate gains (positive deltas) from losses (negative)
            3. Average gain = rolling mean of gains over 14 days
            4. Average loss = rolling mean of losses over 14 days
            5. RS = average_gain / average_loss
            6. RSI = 100 - (100 / (1 + RS))

        EDGE CASES:
            - Pure uptrend (avg_loss == 0, avg_gain > 0) -> RSI = 100
            - Completely flat prices (avg_loss == 0, avg_gain == 0)
              -> RSI = 50 (neutral, no momentum either direction)

        Args:
            series: Series of closing prices
            period: Lookback period (default 14 days — industry standard)
        """
        delta = series.diff()

        # Separate positive and negative changes
        gain = delta.clip(lower=0)    # Losses become 0
        loss = (-delta).clip(lower=0) # Gains become 0

        # Use Wilder's smoothing (ewm with alpha=1/period)
        avg_gain = gain.ewm(
            alpha      = 1 / period,
            adjust     = False,
            min_periods= period
        ).mean()

        avg_loss = loss.ewm(
            alpha      = 1 / period,
            adjust     = False,
            min_periods= period
        ).mean()

        # Avoid division by zero when avg_loss is 0
        rs  = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        # Where avg_loss was 0 AND avg_gain was positive -> RSI = 100
        # (a pure uptrend with zero down-days is maximally overbought)
        rsi = rsi.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)

        # Where both avg_gain and avg_loss are 0 (flat prices) -> RSI = 50
        rsi = rsi.where(~((avg_loss == 0) & (avg_gain == 0)), 50.0)

        return rsi

    # ──────────────────────────────────────────────────────────
    # MACD — MOVING AVERAGE CONVERGENCE DIVERGENCE
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def macd(series: pd.Series,
             fast: int = 12,
             slow: int = 26,
             signal: int = 9) -> pd.DataFrame:
        """
        MACD — Moving Average Convergence Divergence.

        MACD shows the relationship between two EMAs.
        It reveals trend direction and momentum shifts.

        THREE COMPONENTS:
            MACD Line   = EMA(12) - EMA(26)
            Signal Line = EMA(9) of MACD Line
            Histogram   = MACD Line - Signal Line

        INTERPRETATION:
            MACD crosses ABOVE signal → Bullish (buy signal)
            MACD crosses BELOW signal → Bearish (sell signal)
            Histogram growing        → Momentum increasing
            Histogram shrinking      → Momentum weakening

        Args:
            series: Series of closing prices
            fast:   Fast EMA period (default 12)
            slow:   Slow EMA period (default 26)
            signal: Signal line EMA period (default 9)

        Returns:
            DataFrame with columns: macd, signal, histogram
        """
        ema_fast    = TechnicalIndicators.ema(series, fast)
        ema_slow    = TechnicalIndicators.ema(series, slow)

        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(
            span       = signal,
            adjust     = False,
            min_periods= signal
        ).mean()
        histogram   = macd_line - signal_line

        return pd.DataFrame({
            'macd':      macd_line,
            'signal':    signal_line,
            'histogram': histogram,
        })

    # ──────────────────────────────────────────────────────────
    # BOLLINGER BANDS
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def bollinger_bands(series: pd.Series,
                        period: int = 20,
                        std_dev: float = 2.0) -> pd.DataFrame:
        """
        Bollinger Bands.

        Bollinger Bands place volatility envelopes around price.
        When price is quiet, bands narrow. When volatile, they widen.

        THREE BANDS:
            Middle = SMA(20)
            Upper  = SMA(20) + (2 × standard deviation)
            Lower  = SMA(20) - (2 × standard deviation)

        INTERPRETATION:
            Price near upper band → Potentially overbought
            Price near lower band → Potentially oversold
            Bands very narrow    → Volatility squeeze (big move coming)
            Price breaks upper   → Strong upward momentum
            Price breaks lower   → Strong downward momentum

        Args:
            series:  Series of closing prices
            period:  SMA period (default 20)
            std_dev: Number of standard deviations (default 2)

        Returns:
            DataFrame with columns: upper, middle, lower, bandwidth
        """
        middle = TechnicalIndicators.sma(series, period)
        std    = series.rolling(window=period, min_periods=period).std()

        upper  = middle + (std_dev * std)
        lower  = middle - (std_dev * std)

        # Bandwidth measures how wide the bands are
        # Narrow bandwidth = low volatility = potential breakout
        bandwidth = ((upper - lower) / middle) * 100

        return pd.DataFrame({
            'upper':     upper,
            'middle':    middle,
            'lower':     lower,
            'bandwidth': bandwidth,
        })

    # ──────────────────────────────────────────────────────────
    # ATR — AVERAGE TRUE RANGE
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Average True Range (ATR).

        ATR measures market volatility by decomposing the
        entire range of an asset price for a period.

        TRUE RANGE = max of:
            1. high - low          (today's range)
            2. |high - prev_close| (gap up scenario)
            3. |low  - prev_close| (gap down scenario)

        ATR = Rolling average of True Range over N periods.

        WHY USE ATR?
            ATR doesn't tell direction — only volatility.
            Useful for position sizing: higher ATR = wider stops needed.
            Day traders use ATR to set stop-loss distances.

        Args:
            df:     DataFrame with 'high', 'low', 'close' columns
            period: Lookback period (default 14)
        """
        high       = df['high']
        low        = df['low']
        prev_close = df['close'].shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs(),
        ], axis=1).max(axis=1)

        return tr.ewm(
            span       = period,
            adjust     = False,
            min_periods= period
        ).mean()

    # ──────────────────────────────────────────────────────────
    # VWAP — VOLUME WEIGHTED AVERAGE PRICE
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """
        Volume Weighted Average Price (VWAP).

        VWAP is the average price weighted by volume.
        It represents the true average price paid by all
        buyers and sellers throughout the day.

        FORMULA:
            Typical Price = (High + Low + Close) / 3
            VWAP = Cumulative(TP × Volume) / Cumulative(Volume)

        INTERPRETATION:
            Price above VWAP → Bullish (buyers in control)
            Price below VWAP → Bearish (sellers in control)
            Institutions use VWAP as a benchmark — they aim
            to buy below VWAP and sell above it.

        NOTE: True VWAP resets each trading day.
        This implementation gives a rolling approximation
        suitable for daily data analysis.
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        tp_volume     = typical_price * df['volume']

        return tp_volume.cumsum() / df['volume'].cumsum()

    # ──────────────────────────────────────────────────────────
    # RETURNS AND VOLATILITY
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def daily_returns(series: pd.Series) -> pd.Series:
        """
        Daily percentage return.

        Formula: (today's close - yesterday's close) / yesterday's close

        Pandas pct_change() does exactly this in one call.
        Returns are expressed as decimals: 0.02 = 2% gain.
        The first value is always NaN — there's no prior day
        to compare the first observation against.
        """
        return series.pct_change()

    @staticmethod
    def volatility(series: pd.Series, period: int = 21) -> pd.Series:
        """
        Rolling volatility — annualised standard deviation of returns.

        WHY ANNUALISE?
            Daily volatility is tiny and hard to compare.
            Multiplying by sqrt(252) converts daily to annual
            because there are 252 trading days per year.

        A volatility of 0.25 means the stock typically
        moves ±25% per year. Higher = riskier.

        Args:
            series: Series of closing prices
            period: Rolling window in days (default 21 = ~1 month)
        """
        returns = TechnicalIndicators.daily_returns(series)
        return returns.rolling(window=period).std() * np.sqrt(252)

    @staticmethod
    def cumulative_returns(series: pd.Series) -> pd.Series:
        """
        Cumulative return from the first data point.
        Shows total growth if you bought on day 1.

        Formula: (1 + daily_return).cumprod() - 1
        Result: 0.15 means 15% total gain since start.

        EDGE CASE:
            daily_returns() always produces NaN on day one
            (no prior price to compare against). Without
            handling this, cumprod() would propagate that NaN
            into every subsequent value. We fillna(0) first so
            day one is correctly treated as 0% return — the
            natural starting point for a cumulative return series.
        """
        daily = TechnicalIndicators.daily_returns(series).fillna(0)
        return (1 + daily).cumprod() - 1

    # ──────────────────────────────────────────────────────────
    # SIGNAL DETECTION
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def moving_average_crossover(series: pd.Series,
                                  fast: int = 50,
                                  slow: int = 200) -> pd.Series:
        """
        Detects Golden Cross and Death Cross events.

        GOLDEN CROSS: Fast SMA crosses ABOVE slow SMA
            → Bullish signal — historically strong buy indicator
            Classic: 50-day SMA crosses above 200-day SMA

        DEATH CROSS: Fast SMA crosses BELOW slow SMA
            → Bearish signal — potential downtrend ahead

        Returns:
            Series with values:
             1 = Golden Cross (buy signal)
            -1 = Death Cross  (sell signal)
             0 = No crossover
        """
        sma_fast = TechnicalIndicators.sma(series, fast)
        sma_slow = TechnicalIndicators.sma(series, slow)

        # Position: 1 when fast > slow, -1 when fast < slow
        position = np.sign(sma_fast - sma_slow)

        # Crossover happens when position changes
        crossover = position.diff()

        signal = pd.Series(0, index=series.index)
        signal[crossover > 0] =  1   # Golden Cross
        signal[crossover < 0] = -1   # Death Cross

        return signal

    @staticmethod
    def rsi_signals(rsi_series: pd.Series,
                    overbought: float = 70,
                    oversold:   float = 30) -> pd.Series:
        """
        Generates buy/sell signals from RSI values.

        Returns:
             1 = Oversold  (potential buy)
            -1 = Overbought (potential sell)
             0 = Neutral
        """
        signal = pd.Series(0, index=rsi_series.index)
        signal[rsi_series < oversold]   =  1
        signal[rsi_series > overbought] = -1
        return signal