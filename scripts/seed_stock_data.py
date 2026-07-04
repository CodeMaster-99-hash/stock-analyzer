"""
scripts/seed_stock_data.py
===========================
Fetches and saves real market data for all seed stocks.
Run this once after setting up the database.

Usage:
    python scripts\seed_stock_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.logging_service import setup_logging
from database.connection import DatabaseConnection
from services.data_fetcher_service import DataFetcherService

SEED_SYMBOLS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN',
    'TSLA', 'NVDA', 'META', 'JPM', 'JNJ', 'V'
]


def main():
    setup_logging()
    DatabaseConnection.initialise()

    fetcher = DataFetcherService()

    print(f"\nSeeding data for {len(SEED_SYMBOLS)} stocks...")
    print("This will take 1-2 minutes due to API rate limits.\n")

    for i, symbol in enumerate(SEED_SYMBOLS, 1):
        print(f"[{i}/{len(SEED_SYMBOLS)}] Fetching {symbol}...")

        stock = fetcher.fetch_and_save_stock(symbol)
        if stock:
            print(f"  Info : {stock.name} ({stock.sector})")
        else:
            print(f"  Info : FAILED")

        success = fetcher.fetch_and_save_history(symbol, '2y')
        print(f"  History : {'OK' if success else 'FAILED'}")
        print()

    print("Done. Verifying database...")

    import mysql.connector
    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT s.symbol, COUNT(hp.id) as price_records
           FROM stocks s
           LEFT JOIN historical_prices hp ON s.id = hp.stock_id
           GROUP BY s.symbol
           ORDER BY s.symbol"""
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    print(f"\n{'Symbol':<10} {'Price Records':>15}")
    print("-" * 27)
    for row in rows:
        print(f"{row['symbol']:<10} {row['price_records']:>15}")

    total = sum(r['price_records'] for r in rows)
    print("-" * 27)
    print(f"{'TOTAL':<10} {total:>15}")
    print("\nDatabase seeded successfully.")


if __name__ == "__main__":
    main()
