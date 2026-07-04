"""
services/alert_service.py
==========================
Business logic for price alerts.

HOW ALERTS WORK:
    1. User sets an alert: "Tell me when AAPL goes above $200"
    2. Alert is saved to the database (is_active = TRUE)
    3. Every time prices refresh, the alert engine runs
    4. It checks every active alert against the latest price
    5. If the condition is met, it fires a notification
       and marks the alert as triggered (is_active = FALSE)
"""

import logging
from typing import Optional
from models.alert import Alert
from repositories.alert_repository import AlertRepository
from repositories.stock_repository import StockRepository

logger = logging.getLogger(__name__)


class AlertService:
    """Business logic for creating and checking price alerts."""

    def __init__(self,
                 alert_repository: AlertRepository = None,
                 stock_repository: StockRepository = None):
        self.alert_repo = alert_repository or AlertRepository()
        self.stock_repo = stock_repository or StockRepository()

    def create_alert(self, user_id: int, symbol: str,
                     condition: str, target_price: float = None,
                     percent_value: float = None,
                     message: str = None) -> Optional[int]:
        """
        Creates a new price alert.

        Args:
            user_id:       The user creating the alert
            symbol:        Stock ticker e.g. 'AAPL'
            condition:     'ABOVE', 'BELOW', or 'PERCENT_CHANGE'
            target_price:  Price level to trigger at
            percent_value: Percentage change to trigger at
            message:       Custom notification message

        Returns alert ID on success, None on failure.
        """
        stock = self.stock_repo.find_by_symbol(symbol)
        if not stock:
            logger.warning(f"Cannot create alert — unknown stock: {symbol}")
            return None

        try:
            alert = Alert(
                user_id         = user_id,
                stock_id        = stock.id,
                alert_condition = condition.upper(),
                target_price    = target_price,
                percent_value   = percent_value,
                message         = message or self._default_message(
                    symbol, condition, target_price, percent_value
                ),
            )
            alert_id = self.alert_repo.save(alert)
            logger.info(
                f"Alert created for {symbol} — "
                f"{condition} {target_price or percent_value}"
            )
            return alert_id
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None

    def check_alerts(self, current_prices: dict) -> list[dict]:
        """
        Checks all active alerts against current prices.
        Called by the scheduler on every price refresh.

        Args:
            current_prices: Dict mapping symbol to current price
                            e.g. {'AAPL': 205.50, 'MSFT': 420.00}

        Returns list of triggered alert dicts.
        """
        triggered = []
        try:
            active_alerts = self.alert_repo.find_active_alerts()
        except Exception as e:
            logger.error(f"Failed to fetch active alerts: {e}")
            return []

        for alert in active_alerts:
            symbol = getattr(alert, 'symbol', None)
            if not symbol or symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            fired         = False

            if alert.alert_condition == 'ABOVE':
                fired = (
                    alert.target_price is not None and
                    current_price > float(alert.target_price)
                )

            elif alert.alert_condition == 'BELOW':
                fired = (
                    alert.target_price is not None and
                    current_price < float(alert.target_price)
                )

            elif alert.alert_condition == 'PERCENT_CHANGE':
                latest = self.stock_repo.get_latest_price(alert.stock_id)
                if latest:
                    prev_price = float(latest.get('close_price', 0))
                    if prev_price:
                        pct_change = abs(
                            (current_price - prev_price) / prev_price * 100
                        )
                        fired = (
                            alert.percent_value is not None and
                            pct_change >= float(alert.percent_value)
                        )

            if fired:
                logger.info(
                    f"Alert triggered: {symbol} "
                    f"{alert.alert_condition} "
                    f"{alert.target_price or alert.percent_value}"
                )
                self.alert_repo.mark_triggered(alert.id)
                triggered.append({
                    'alert_id':  alert.id,
                    'symbol':    symbol,
                    'condition': alert.alert_condition,
                    'message':   alert.message,
                    'price':     current_price,
                })

        return triggered

    def get_user_alerts(self, user_id: int) -> list[Alert]:
        """Returns all alerts for a user."""
        try:
            return self.alert_repo.find_by_user(user_id)
        except Exception as e:
            logger.error(f"Failed to get alerts for user {user_id}: {e}")
            return []

    def delete_alert(self, alert_id: int) -> bool:
        """Deletes an alert. Returns True on success."""
        try:
            self.alert_repo.delete(alert_id)
            logger.info(f"Alert deleted: id={alert_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete alert {alert_id}: {e}")
            return False

    @staticmethod
    def _default_message(symbol: str, condition: str,
                          target_price: float,
                          percent_value: float) -> str:
        """Generates a default alert message."""
        if condition == 'ABOVE':
            return f"{symbol} has risen above ${target_price:.2f}"
        elif condition == 'BELOW':
            return f"{symbol} has fallen below ${target_price:.2f}"
        elif condition == 'PERCENT_CHANGE':
            return f"{symbol} has moved {percent_value:.1f}%"
        return f"Alert triggered for {symbol}"
