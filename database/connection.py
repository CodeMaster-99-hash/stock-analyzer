"""
database/connection.py
======================
Manages the MySQL database connection pool.

WHY A CONNECTION POOL?
    Opening a new database connection takes ~50ms.
    If we open a new connection for every query, the app feels sluggish.
    A connection pool keeps connections open and reuses them.
    mysql-connector-python handles this for us automatically.
"""

import mysql.connector
from mysql.connector import pooling, Error
import os
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Singleton class that manages a MySQL connection pool.

    WHY SINGLETON?
        We only ever want ONE connection pool for the entire app.
        If we created multiple pools, we'd waste memory and connections.
    """

    _pool = None  # The single shared connection pool

    @classmethod
    def initialise(cls) -> None:
        """
        Creates the connection pool on first call.
        Must be called once at application startup (in main.py).
        """
        if cls._pool is not None:
            return  # Already initialised — do nothing

        try:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name="stock_analyzer_pool",
                pool_size=10,          # 10 simultaneous connections
                pool_reset_session=True,
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 3306)),
                database=os.getenv("DB_NAME", "stock_analyzer"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", "812574@Rj"),
                charset="utf8mb4",
                autocommit=False,     # We control transactions explicitly
            )
            logger.info("Database connection pool created successfully.")

        except Error as e:
            logger.critical(f"Failed to create connection pool: {e}")
            raise

    @classmethod
    def get_connection(cls):
        """
        Returns a connection from the pool.

        USAGE:
            conn = DatabaseConnection.get_connection()
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM stocks")
                results = cursor.fetchall()
            finally:
                conn.close()  # Returns connection to pool — does NOT close it
        """
        if cls._pool is None:
            cls.initialise()

        try:
            return cls._pool.get_connection()
        except Error as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
