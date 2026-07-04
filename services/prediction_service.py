"""
services/prediction_service.py
================================
Orchestrates model training, prediction, and saving
results to MySQL.
"""

import logging
from database.connection import DatabaseConnection
from services.analytics_service import AnalyticsService
from repositories.stock_repository import StockRepository
from prediction.model_trainer import ModelTrainer
from prediction.predictor import Predictor

logger = logging.getLogger(__name__)


class PredictionService:
    """Coordinates the full ML prediction pipeline."""

    def __init__(self):
        self.analytics  = AnalyticsService()
        self.stock_repo = StockRepository()
        self.trainer    = ModelTrainer()
        self.predictor  = Predictor()

    def train_models_for_stock(self, symbol: str,
                                target_horizon: int = 1) -> dict:
        """
        Trains all three models for a stock and returns
        comparison metrics.
        """
        df = self.analytics.get_enriched_data(symbol, period_days=730)
        if df.empty:
            logger.warning(f"No data available to train models for {symbol}")
            return {}

        results = self.trainer.train_all_models(df, symbol, target_horizon)
        return results

    def get_prediction(self, symbol: str,
                        target_horizon: int = 1) -> dict:
        """
        Gets a price prediction for a stock using the best
        available trained model.
        """
        df = self.analytics.get_enriched_data(symbol, period_days=730)
        if df.empty:
            return {}

        result = self.predictor.predict_next_price(
            df, symbol, target_horizon=target_horizon
        )

        if result:
            self._save_prediction_to_db(symbol, result)

        return result

    def _save_prediction_to_db(self, symbol: str, result: dict):
        """Saves a prediction to the predictions table."""
        stock = self.stock_repo.find_by_symbol(symbol)
        if not stock:
            return

        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO predictions
                   (stock_id, model_name, predicted_price,
                    prediction_date, horizon_days, confidence)
                   VALUES (%s, %s, %s, CURDATE(), %s, %s)""",
                (
                    stock.id,
                    result['model_used'],
                    result['predicted_price'],
                    result['horizon_days'],
                    result['confidence'],
                )
            )
            conn.commit()
            cursor.close()
            logger.info(f"Prediction saved for {symbol}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save prediction for {symbol}: {e}")
        finally:
            conn.close()

    def train_all_watchlist_models(self, symbols: list) -> dict:
        """
        Trains models for every stock in the watchlist.
        Run this once to populate ml_artifacts/ before
        using predictions in the GUI.
        """
        all_results = {}
        for symbol in symbols:
            logger.info(f"Training models for {symbol}...")
            results = self.train_models_for_stock(symbol)
            all_results[symbol] = results
        return all_results