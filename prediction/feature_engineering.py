"""
prediction/feature_engineering.py
===================================
Converts enriched price data into features suitable
for machine learning models.

WHAT IS A "FEATURE" IN ML?
    A feature is any input variable the model uses to predict
    the target. If we want to predict tomorrow's closing price,
    features might be: today's RSI, today's volume, yesterday's
    close, the 5-day average, etc.

WHY NOT JUST USE RAW PRICE AS THE ONLY FEATURE?
    A model trained only on "yesterday's price predicts today's
    price" just learns to copy the last value — useless.
    Good features capture PATTERNS: momentum, volatility,
    trend strength, volume behaviour. The model learns how
    these patterns relate to future price movement.
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureEngineering:
    """
    Builds ML-ready feature matrices from enriched price DataFrames.
    """

    @staticmethod
    def build_features(df: pd.DataFrame,
                        target_horizon: int = 1) -> pd.DataFrame:
        """
        Builds the full feature set plus the prediction target.

        Args:
            df:             Enriched DataFrame from DataProcessor
                            (must already have indicators calculated)
            target_horizon: How many days ahead to predict
                            (1 = next day, 5 = next week)

        Returns:
            DataFrame with feature columns + 'target' column.
            Rows with any NaN are dropped (early rows lack
            enough history for indicators like SMA200).
        """
        if df.empty or len(df) < 250:
            logger.warning(
                "Not enough data for feature engineering "
                "(need 250+ rows for SMA200 to be valid)"
            )
            return pd.DataFrame()

        feat = pd.DataFrame(index=df.index)

        # ── Lagged price features ────────────────────────────
        # "Where was the price N days ago relative to today?"
        for lag in [1, 2, 3, 5, 10]:
            feat[f'return_lag_{lag}'] = df['close'].pct_change(lag)

        # ── Indicator features (already calculated in Phase 7) ─
        feat['rsi_14']       = df['rsi_14']
        feat['macd']         = df['macd']
        feat['macd_hist']    = df['macd_hist']
        feat['bb_width']     = df['bb_width']
        feat['volatility_21']= df['volatility_21']
        feat['atr_14']       = df['atr_14']

        # ── Price relative to moving averages ────────────────
        # Ratio rather than raw value — makes the feature scale-
        # independent. A $1500 stock and a $15 stock both produce
        # values around 1.0 when price equals its SMA.
        feat['price_to_sma20']  = df['close'] / df['sma_20']
        feat['price_to_sma50']  = df['close'] / df['sma_50']
        feat['price_to_sma200'] = df['close'] / df['sma_200']
        feat['sma20_to_sma50']  = df['sma_20'] / df['sma_50']

        # ── Volume features ───────────────────────────────────
        feat['volume_change']   = df['volume'].pct_change()
        feat['volume_sma_ratio']= (
            df['volume'] / df['volume'].rolling(20).mean()
        )

        # ── Bollinger Band position ──────────────────────────
        # 0 = at lower band, 1 = at upper band, 0.5 = at middle
        feat['bb_position'] = (
            (df['close'] - df['bb_lower']) /
            (df['bb_upper'] - df['bb_lower']).replace(0, np.nan)
        )

        # ── Day of week (markets behave slightly differently) ──
        feat['day_of_week'] = df.index.dayofweek

        # ── TARGET — what we want to predict ──────────────────
        # Future return N days ahead, expressed as a percentage.
        # shift(-horizon) looks FORWARD in time.
        feat['target'] = (
            df['close'].shift(-target_horizon) / df['close'] - 1
        ) * 100

        # Drop rows with any NaN (early indicator warm-up period
        # and the last `target_horizon` rows which have no future
        # price to compute the target against)
        feat = feat.replace([np.inf, -np.inf], np.nan)
        before = len(feat)
        feat = feat.dropna()
        after = len(feat)

        logger.info(
            f"Feature engineering: {before} rows -> {after} rows "
            f"after dropping NaN ({before - after} removed)"
        )

        return feat

    @staticmethod
    def get_feature_columns() -> list:
        """
        Returns the list of feature column names (excludes target).
        Used to ensure train and predict use identical feature sets.
        """
        return [
            'return_lag_1', 'return_lag_2', 'return_lag_3',
            'return_lag_5', 'return_lag_10',
            'rsi_14', 'macd', 'macd_hist', 'bb_width',
            'volatility_21', 'atr_14',
            'price_to_sma20', 'price_to_sma50', 'price_to_sma200',
            'sma20_to_sma50',
            'volume_change', 'volume_sma_ratio',
            'bb_position', 'day_of_week',
        ]