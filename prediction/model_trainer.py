"""
prediction/model_trainer.py
=============================
Trains and evaluates ML models for price prediction.

WHY THREE DIFFERENT MODELS?
    Linear Regression  — simple, fast, interpretable baseline.
                         Assumes a straight-line relationship.
    Random Forest       — an ensemble of decision trees. Captures
                         non-linear patterns. Less prone to overfitting
                         than a single tree.
    XGBoost             — gradient boosting. Usually the strongest
                         performer on tabular data like this.

We train all three and keep whichever performs best on unseen
test data. This is standard practice — never assume one algorithm
is "best" without testing.
"""

import logging
import numpy as np
import pandas as pd
import joblib
import os
from datetime import datetime

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score
)
import xgboost as xgb

from prediction.feature_engineering import FeatureEngineering

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'ml_artifacts'
)


class ModelTrainer:
    """
    Trains, evaluates, and persists ML prediction models.
    """

    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)

    def train_all_models(self, df: pd.DataFrame, symbol: str,
                          target_horizon: int = 1) -> dict:
        """
        Trains Linear Regression, Random Forest, and XGBoost
        on the given stock's data, then compares them.

        WHY TimeSeriesSplit INSTEAD OF RANDOM SPLIT?
            Normal train_test_split shuffles rows randomly.
            For time series, that's a serious mistake — it lets
            the model "see the future" during training (e.g. train
            on March 15 data, test on March 10). TimeSeriesSplit
            always trains on earlier dates and tests on later ones,
            matching how the model will actually be used.

        Args:
            df:             Enriched price DataFrame
            symbol:         Stock ticker
            target_horizon: Days ahead to predict (1 = next day)

        Returns:
            Dict with results for each model:
            {
                'linear_regression': {...metrics...},
                'random_forest':     {...metrics...},
                'xgboost':            {...metrics...},
                'best_model':        'xgboost',
            }
        """
        features = FeatureEngineering.build_features(df, target_horizon)
        if features.empty or len(features) < 100:
            logger.warning(
                f"Not enough feature rows to train for {symbol} "
                f"(have {len(features)}, need 100+)"
            )
            return {}

        feature_cols = FeatureEngineering.get_feature_columns()
        X = features[feature_cols]
        y = features['target']

        # ── Time-respecting split: last 20% of dates = test set ─
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        logger.info(
            f"Training on {len(X_train)} rows, "
            f"testing on {len(X_test)} rows"
        )

        # ── Scale features ────────────────────────────────────
        # WHY SCALE? Linear Regression is sensitive to feature
        # magnitude — RSI (0-100) would dominate over bb_position
        # (0-1) purely due to scale, not actual importance.
        # Tree-based models (RF, XGBoost) don't strictly need this
        # but it doesn't hurt and keeps the pipeline consistent.
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled  = scaler.transform(X_test)

        results = {}

        # ── Model 1: Linear Regression ───────────────────────
        lr = LinearRegression()
        lr.fit(X_train_scaled, y_train)
        results['linear_regression'] = self._evaluate(
            lr, X_test_scaled, y_test, 'Linear Regression'
        )

        # ── Model 2: Random Forest ────────────────────────────
        rf = RandomForestRegressor(
            n_estimators = 200,
            max_depth    = 8,
            min_samples_leaf = 10,
            random_state = 42,
            n_jobs       = -1,
        )
        rf.fit(X_train, y_train)   # Trees don't need scaling
        results['random_forest'] = self._evaluate(
            rf, X_test, y_test, 'Random Forest'
        )

        # ── Model 3: XGBoost ──────────────────────────────────
        xgb_model = xgb.XGBRegressor(
            n_estimators  = 200,
            max_depth     = 4,
            learning_rate = 0.05,
            subsample     = 0.8,
            colsample_bytree = 0.8,
            random_state  = 42,
        )
        xgb_model.fit(X_train, y_train)
        results['xgboost'] = self._evaluate(
            xgb_model, X_test, y_test, 'XGBoost'
        )

        # ── Pick the best model by lowest RMSE ───────────────
        best_name = min(
            results, key=lambda k: results[k]['rmse']
        )
        results['best_model'] = best_name
        logger.info(
            f"Best model for {symbol}: {best_name} "
            f"(RMSE={results[best_name]['rmse']:.4f})"
        )

        # ── Save the best model and scaler to disk ───────────
        self._save_model(
            symbol,
            {'linear_regression': lr,
             'random_forest':     rf,
             'xgboost':            xgb_model}[best_name],
            scaler if best_name == 'linear_regression' else None,
            best_name,
            target_horizon,
        )

        return results

    def _evaluate(self, model, X_test, y_test, name: str) -> dict:
        """
        Evaluates a trained model on test data.

        METRICS EXPLAINED:
            MAE  (Mean Absolute Error) — average prediction error
                 in the same units as the target (% return here).
                 MAE of 1.5 means predictions are off by 1.5% on
                 average. Easy to interpret.

            RMSE (Root Mean Squared Error) — similar to MAE but
                 penalises large errors more heavily (squares them
                 before averaging). If RMSE >> MAE, the model has
                 some very wrong predictions mixed with mostly
                 good ones.

            R²   (R-squared) — fraction of variance explained,
                 from -inf to 1.0. R²=1 is perfect prediction.
                 R²=0 means the model is no better than always
                 predicting the average. R² < 0 means WORSE than
                 just guessing the average — common for stock
                 prediction since markets are largely random.
        """
        predictions = model.predict(X_test)

        mae  = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        r2   = r2_score(y_test, predictions)

        # Directional accuracy — did we at least get up/down right?
        # This often matters more than exact value for trading.
        actual_direction    = np.sign(y_test)
        predicted_direction = np.sign(predictions)
        directional_accuracy = (
            (actual_direction == predicted_direction).mean() * 100
        )

        logger.info(
            f"{name}: MAE={mae:.4f}  RMSE={rmse:.4f}  "
            f"R2={r2:.4f}  Dir.Acc={directional_accuracy:.1f}%"
        )

        return {
            'mae':                  round(float(mae), 4),
            'rmse':                 round(float(rmse), 4),
            'r2_score':             round(float(r2), 4),
            'directional_accuracy': round(float(directional_accuracy), 2),
        }

    def _save_model(self, symbol: str, model, scaler,
                     model_name: str, target_horizon: int):
        """
        Saves the trained model (and scaler if needed) to disk
        using joblib — the standard for scikit-learn model
        persistence.
        """
        path = os.path.join(
            MODEL_DIR, f"{symbol}_{model_name}_h{target_horizon}.pkl"
        )
        payload = {
            'model':          model,
            'scaler':         scaler,
            'model_name':     model_name,
            'target_horizon': target_horizon,
            'feature_cols':   FeatureEngineering.get_feature_columns(),
            'trained_at':     datetime.now().isoformat(),
        }
        joblib.dump(payload, path)
        logger.info(f"Model saved: {path}")

    def load_model(self, symbol: str, model_name: str,
                    target_horizon: int = 1) -> dict:
        """Loads a previously trained model from disk."""
        path = os.path.join(
            MODEL_DIR, f"{symbol}_{model_name}_h{target_horizon}.pkl"
        )
        if not os.path.exists(path):
            logger.warning(f"No saved model found at {path}")
            return None
        return joblib.load(path)