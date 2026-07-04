"""
repositories/base_repository.py
================================
Base class for all repositories.

WHY A BASE CLASS?
    Every repository needs to:
        1. Get a connection from the pool
        2. Create a cursor
        3. Execute a query
        4. Handle errors
        5. Close the connection

    Without a base class we'd copy that pattern into every repository.
    Instead, we write it once here and all repositories inherit it.
    This is the DRY principle — Don't Repeat Yourself.
"""

import logging
from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Parent class for all repositories.
    Provides shared database access methods.
    """

    def _get_connection(self):
        """
        Returns a connection from the pool.
        Always use this instead of DatabaseConnection directly.
        """
        return DatabaseConnection.get_connection()

    def _execute_query(self, query: str, params: tuple = None) -> list:
        """
        Executes a SELECT query and returns all rows as a list of dicts.

        WHY dictionary=True ON THE CURSOR?
            By default MySQL cursor returns rows as tuples:
                (1, 'AAPL', 'Apple Inc.')

            With dictionary=True it returns dicts:
                {'id': 1, 'symbol': 'AAPL', 'name': 'Apple Inc.'}

            Dicts are much safer — order doesn't matter and
            the keys are self-documenting.

        Args:
            query:  SQL SELECT statement with %s placeholders
            params: Tuple of values to safely substitute into query

        Returns:
            List of dicts, one per row
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Query failed: {e} | Query: {query} | Params: {params}")
            raise
        finally:
            conn.close()  # Returns connection to pool

    def _execute_write(self, query: str, params: tuple = None) -> int:
        """
        Executes an INSERT, UPDATE, or DELETE query.

        WHY conn.commit()?
            MySQL with autocommit=False (our setting) does not save
            changes until you explicitly call commit().
            If something goes wrong, conn.rollback() undoes everything
            since the last commit — protecting data integrity.

        Args:
            query:  SQL INSERT/UPDATE/DELETE with %s placeholders
            params: Tuple of values

        Returns:
            lastrowid for INSERT (the new row's id), or rowcount for UPDATE/DELETE
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            last_id = cursor.lastrowid
            cursor.close()
            return last_id
        except Exception as e:
            conn.rollback()  # Undo any changes if something went wrong
            logger.error(f"Write failed: {e} | Query: {query} | Params: {params}")
            raise
        finally:
            conn.close()

    def _execute_many(self, query: str, params_list: list) -> int:
        """
        Executes the same query for multiple rows at once.
        Much faster than calling _execute_write in a loop.

        Used when inserting bulk historical price data —
        thousands of rows at once instead of one at a time.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            count = cursor.rowcount
            cursor.close()
            return count
        except Exception as e:
            conn.rollback()
            logger.error(f"Bulk write failed: {e}")
            raise
        finally:
            conn.close()
