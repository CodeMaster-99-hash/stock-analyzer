"""
scripts/train_models.py
=========================
Trains ML models for all watchlist stocks.
Run this once before using predictions in the GUI,
and re-run periodically (e.g. weekly) to keep models fresh.

Usage:
    python scripts\train_models.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.logging_service import setup_logging
from database.connection import DatabaseConnection
from services.prediction_service import PredictionService

WATCHLIST_SYMBOLS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN',
    'TSLA', 'NVDA', 'META', 'JPM', 'JNJ', 'V'
]


def main():
    setup_logging()
    DatabaseConnection.initialise()

    svc = PredictionService()

    print(f"\nTraining ML models for {len(WATCHLIST_SYMBOLS)} stocks...")
    print("This will take several minutes.\n")

    summary = []

    for symbol in WATCHLIST_SYMBOLS:
        print(f"--- {symbol} ---")
        results = svc.train_models_for_stock(symbol)

        if not results:
            print(f"  SKIPPED (insufficient data)\n")
            continue

        best = results.get('best_model', 'N/A')
        best_metrics = results.get(best, {})

        print(f"  Best model : {best}")
        print(f"  RMSE       : {best_metrics.get('rmse')}")
        print(f"  Dir. Acc.  : {best_metrics.get('directional_accuracy')}%")
        print()

        summary.append({
            'symbol': symbol,
            'best_model': best,
            'rmse': best_metrics.get('rmse'),
            'directional_accuracy': best_metrics.get('directional_accuracy'),
        })

    print("=" * 60)
    print(f"{'Symbol':<10}{'Best Model':<20}{'RMSE':<10}{'Dir.Acc%':<10}")
    print("-" * 60)
    for s in summary:
        print(
            f"{s['symbol']:<10}{s['best_model']:<20}"
            f"{s['rmse']:<10}{s['directional_accuracy']:<10}"
        )
    print("=" * 60)
    print(f"\nModels saved to: ml_artifacts/")
    print("Training complete.")


if __name__ == "__main__":
    main()