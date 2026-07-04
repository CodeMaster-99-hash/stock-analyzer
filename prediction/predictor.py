"""
prediction/predictor.py
=========================
Uses trained models to predict future stock prices.
"""

import logging
import numpy as np
import pandas as pd
from prediction.feature_engineering import FeatureEngineering
from prediction.model_trainer import ModelTrainer

logger = logging.getLogger(__name__)


class Predictor:
    """
    Loads trained models and generates predictions
    on the most recent data.
    """

    def __init__(self):
        self.trainer = ModelTrainer()

    def predict_next_price(self, df: pd.DataFrame, symbol: str,
                            model_name: str = None,
                            target_horizon: int = 1) -> dict:
        """
        Predicts the price movement N days ahead using the
        most recent available data.

        Args:
            df:             Enriched price DataFrame (must include
                            the latest trading day)
            symbol:         Stock ticker
            model_name:     'linear_regression', 'random_forest',
                            'xgboost', or None to auto-detect best
            target_horizon: Days ahead the model was trained for

        Returns:
            {
                'symbol':           'AAPL',
                'current_price':    189.50,
                'predicted_return_pct': 1.85,
                'predicted_price':  193.00,
                'confidence':       0.62,
                'model_used':       'xgboost',
                'direction':        'UP',
            }
            Or empty dict if no model is available.
        """
        # Build features the same way training did
        features = FeatureEngineering.build_features(df, target_horizon)
        if features.empty:
            logger.warning(f"No features available to predict {symbol}")
            return {}

        # Try to load the requested model, or find any available one
        payload = None
        if model_name:
            payload = self.trainer.load_model(
                symbol, model_name, target_horizon
            )

        if payload is None:
            for candidate in ['xgboost', 'random_forest', 'linear_regression']:
                payload = self.trainer.load_model(
                    symbol, candidate, target_horizon
                )
                if payload:
                    model_name = candidate
                    break

        if payload is None:
            logger.warning(
                f"No trained model found for {symbol}. "
                f"Run train_all_models() first."
            )
            return {}

        model        = payload['model']
        scaler       = payload['scaler']
        feature_cols = payload['feature_cols']

        # Use the most recent row of features (today's data)
        latest_features = features[feature_cols].iloc[[-1]]

        if scaler is not None:
            latest_features = scaler.transform(latest_features)

        predicted_return_pct = float(model.predict(latest_features)[0])

        current_price   = float(df['close'].iloc[-1])
        predicted_price = current_price * (1 + predicted_return_pct / 100)

        # Simple confidence proxy based on recent volatility —
        # lower volatility periods tend to have more reliable
        # short-term predictions
        recent_volatility = float(
            df['volatility_21'].iloc[-1]
        ) if 'volatility_21' in df.columns else 0.3
        confidence = max(0.1, min(0.9, 1 - recent_volatility))

        direction = (
            'UP' if predicted_return_pct > 0.1 else
            'DOWN' if predicted_return_pct < -0.1 else
            'FLAT'
        )

        logger.info(
            f"{symbol} prediction ({model_name}): "
            f"{predicted_return_pct:+.2f}% -> ${predicted_price:.2f} "
            f"({direction})"
        )

        return {
            'symbol':               symbol,
            'current_price':        round(current_price, 2),
            'predicted_return_pct': round(predicted_return_pct, 2),
            'predicted_price':      round(predicted_price, 2),
            'confidence':           round(confidence, 2),
            'model_used':           model_name,
            'horizon_days':         target_horizon,
            'direction':            direction,
        }