"""
repositories/alert_repository.py
==================================
Database operations for price alerts.
"""

import logging
from models.alert import Alert
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AlertRepository(BaseRepository):
    """Handles all database operations for alerts."""

    def find_active_alerts(self) -> list[Alert]:
        """
        Returns all active alerts across all users.
        The alert engine calls this on every price refresh
        to check which alerts should fire.
        """
        rows = self._execute_query(
            """SELECT a.*, s.symbol, s.name as stock_name
               FROM alerts a
               JOIN stocks s ON a.stock_id = s.id
               WHERE a.is_active = TRUE
               ORDER BY a.created_at"""
        )
        return [Alert.from_dict(row) for row in rows]

    def find_by_user(self, user_id: int) -> list[Alert]:
        """Returns all alerts set by a specific user."""
        rows = self._execute_query(
            """SELECT a.*, s.symbol, s.name as stock_name
               FROM alerts a
               JOIN stocks s ON a.stock_id = s.id
               WHERE a.user_id = %s
               ORDER BY a.created_at DESC""",
            (user_id,)
        )
        return [Alert.from_dict(row) for row in rows]

    def save(self, alert: Alert) -> int:
        """Creates a new alert and returns its ID."""
        return self._execute_write(
            """INSERT INTO alerts
               (user_id, stock_id, alert_condition,
                target_price, percent_value, message)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                alert.user_id,
                alert.stock_id,
                alert.alert_condition,
                alert.target_price,
                alert.percent_value,
                alert.message,
            )
        )

    def mark_triggered(self, alert_id: int) -> None:
        """Marks an alert as triggered so it doesn't fire again."""
        self._execute_write(
            """UPDATE alerts
               SET is_active = FALSE, triggered_at = NOW()
               WHERE id = %s""",
            (alert_id,)
        )

    def delete(self, alert_id: int) -> None:
        """Deletes an alert permanently."""
        self._execute_write(
            "DELETE FROM alerts WHERE id = %s",
            (alert_id,)
        )
