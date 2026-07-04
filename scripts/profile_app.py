"""
scripts/profile_app.py
========================
Measures how long key operations actually take.
Run this BEFORE optimizing to know what's actually slow,
and AFTER to confirm the optimization worked.

Usage:
    python scripts\profile_app.py
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.logging_service import setup_logging
from database.connection import DatabaseConnection


def timed(label):
    """Decorator-like context manager for timing operations."""
    class Timer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self
        def __exit__(self, *args):
            elapsed = (time.perf_counter() - self.start) * 1000
            print(f"  {label:<45} {elapsed:>8.2f} ms")
    return Timer()


def main():
    setup_logging()
    DatabaseConnection.initialise()

    print("\n" + "=" * 60)
    print("PERFORMANCE PROFILE")
    print("=" * 60)

    from repositories.stock_repository import StockRepository
    from services.stock_service import StockService
    from services.analytics_service import AnalyticsService
    from controllers.stock_controller import StockController

    repo       = StockRepository()
    service    = StockService(repo)
    analytics  = AnalyticsService(repo)
    controller = StockController(service)

    print("\n[Database Layer]")
    with timed("find_all() — get all stocks"):
        repo.find_all()

    with timed("find_by_symbol('AAPL')"):
        repo.find_by_symbol('AAPL')

    with timed("search('app')"):
        repo.search('app')

    stock = repo.find_by_symbol('AAPL')
    with timed("get_historical_prices() — 1 year"):
        repo.get_historical_prices(
            stock.id, '2024-01-01', '2025-12-31'
        )

    print("\n[Analytics Layer]")
    with timed("get_enriched_data() — load + clean + indicators"):
        df = analytics.get_enriched_data('AAPL', 365)

    with timed("get_enriched_data() — SECOND call (no cache yet)"):
        df = analytics.get_enriched_data('AAPL', 365)

    print("\n[Controller Layer — GUI-facing]")
    with timed("controller.search('AAPL')"):
        controller.search('AAPL')

    with timed("controller.get_price_history('AAPL')"):
        controller.get_price_history('AAPL')

    print("\n[Multi-stock batch — Dashboard load simulation]")
    symbols = ['AAPL','MSFT','GOOGL','AMZN','TSLA','NVDA','META','JPM']
    with timed(f"8x get_stock_detail() sequential"):
        for s in symbols:
            controller.get_stock_detail(s)

    with timed(f"8x get_price_change() sequential"):
        for s in symbols:
            controller.get_price_change(s)

    print("\n" + "=" * 60)
    print("Profile complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()