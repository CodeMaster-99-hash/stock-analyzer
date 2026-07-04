"""
tests/test_technical_indicators.py
====================================
Unit tests for technical indicator calculations.

STRATEGY: Use small datasets with KNOWN expected results,
calculated by hand, so we can verify the formulas are
implemented correctly — not just "doesn't crash."
"""

import pytest
import pandas as pd
import numpy as np
from analytics.technical_indicators import TechnicalIndicators as TI


class TestMovingAverages:

    def test_sma_basic_calculation(self):
        """
        SMA(3) of [10, 11, 12, 13, 14]:
        Day 3: (10+11+12)/3 = 11.0
        Day 4: (11+12+13)/3 = 12.0
        Day 5: (12+13+14)/3 = 13.0
        """
        prices = pd.Series([10, 11, 12, 13, 14])
        sma = TI.sma(prices, period=3)

        assert pd.isna(sma.iloc[0])   # Not enough history
        assert pd.isna(sma.iloc[1])
        assert sma.iloc[2] == 11.0
        assert sma.iloc[3] == 12.0
        assert sma.iloc[4] == 13.0

    def test_sma_constant_prices(self):
        """SMA of constant prices should equal that constant."""
        prices = pd.Series([50.0] * 10)
        sma = TI.sma(prices, period=5)
        assert sma.iloc[-1] == 50.0

    def test_ema_reacts_faster_than_sma(self):
        """
        EMA should be closer to recent prices than SMA
        because it weights recent data more heavily.
        """
        # Flat then a sudden jump
        prices = pd.Series([100]*20 + [150]*5)
        sma = TI.sma(prices, period=10)
        ema = TI.ema(prices, period=10)

        # After the jump, EMA should have moved further toward
        # the new price than SMA
        assert ema.iloc[-1] > sma.iloc[-1]


class TestRSI:

    def test_rsi_bounded_between_0_and_100(self):
        """RSI must always be between 0 and 100."""
        np.random.seed(42)
        prices = pd.Series(100 + np.cumsum(np.random.randn(100)))
        rsi = TI.rsi(prices, period=14)

        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_high_for_consistent_gains(self):
        """A consistently rising price should produce high RSI."""
        prices = pd.Series(range(100, 130))  # Steady increase
        rsi = TI.rsi(prices, period=14)
        assert rsi.iloc[-1] > 70   # Should signal overbought

    def test_rsi_low_for_consistent_losses(self):
        """A consistently falling price should produce low RSI."""
        prices = pd.Series(range(130, 100, -1))  # Steady decrease
        rsi = TI.rsi(prices, period=14)
        assert rsi.iloc[-1] < 30   # Should signal oversold


class TestMACD:

    def test_macd_returns_three_columns(self, sample_price_dataframe):
        """MACD should return macd, signal, and histogram columns."""
        result = TI.macd(sample_price_dataframe['close'])
        assert set(result.columns) == {'macd', 'signal', 'histogram'}

    def test_macd_histogram_equals_macd_minus_signal(self):
        """histogram should always equal macd - signal exactly."""
        prices = pd.Series(100 + np.cumsum(np.random.randn(60)))
        result = TI.macd(prices)

        valid = result.dropna()
        diff = valid['macd'] - valid['signal']
        # Allow tiny floating point tolerance
        assert np.allclose(valid['histogram'], diff, atol=1e-9)


class TestBollingerBands:

    def test_price_within_bands_for_normal_volatility(self):
        """
        For normally distributed returns, most prices should
        fall within the upper and lower bands (2 std devs).
        """
        np.random.seed(1)
        prices = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5))
        bb = TI.bollinger_bands(prices, period=20, std_dev=2.0)

        valid_idx = bb.dropna().index
        within_bands = (
            (prices[valid_idx] <= bb.loc[valid_idx, 'upper']) &
            (prices[valid_idx] >= bb.loc[valid_idx, 'lower'])
        )
        # At least 90% of prices should be within 2-std bands
        assert within_bands.mean() > 0.90

    def test_middle_band_equals_sma(self, sample_price_dataframe):
        """The middle band must equal a simple SMA of the same period."""
        close = sample_price_dataframe['close']
        bb  = TI.bollinger_bands(close, period=20)
        sma = TI.sma(close, period=20)
        pd.testing.assert_series_equal(
            bb['middle'], sma, check_names=False
        )


class TestATR:

    def test_atr_is_never_negative(self, sample_price_dataframe):
        """True Range and ATR can never be negative — it's a range."""
        atr = TI.atr(sample_price_dataframe, period=14)
        valid_atr = atr.dropna()
        assert (valid_atr >= 0).all()


class TestReturnsAndVolatility:

    def test_daily_returns_calculation(self):
        """Daily return of [100, 110] should be exactly 0.10 (10%)."""
        prices = pd.Series([100, 110])
        returns = TI.daily_returns(prices)
        assert returns.iloc[1] == pytest.approx(0.10)

    def test_volatility_is_non_negative(self, sample_price_dataframe):
        """Volatility (a standard deviation) can never be negative."""
        vol = TI.volatility(sample_price_dataframe['close'], period=10)
        valid_vol = vol.dropna()
        assert (valid_vol >= 0).all()

    def test_cumulative_return_starts_near_zero(self):
        """First cumulative return value should be 0 (no change yet)."""
        prices = pd.Series([100, 105, 110, 108])
        cum_ret = TI.cumulative_returns(prices)
        assert cum_ret.iloc[0] == 0.0


class TestSignals:

    def test_golden_cross_detected(self):
        """
        Construct prices where a short MA crosses above a long MA
        and verify the signal fires with value +1.
        """
        # Declining then rising sharply — forces a crossover
        prices = pd.Series(
            list(range(100, 80, -1)) + list(range(80, 140, 2))
        )
        signal = TI.moving_average_crossover(prices, fast=5, slow=15)
        assert (signal == 1).any()   # At least one Golden Cross

    def test_rsi_signals_oversold_detected(self):
        """RSI signal should mark oversold (1) when RSI < 30."""
        rsi_values = pd.Series([25, 28, 35, 50, 75, 80])
        signal = TI.rsi_signals(rsi_values, overbought=70, oversold=30)
        assert signal.iloc[0] == 1    # 25 < 30 → oversold
        assert signal.iloc[4] == -1   # 75 > 70 → overbought
        assert signal.iloc[3] == 0    # 50 → neutral