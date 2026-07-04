"""
controllers/alert_controller.py
================================
Bridges the GUI and AlertService.
"""

import logging
from services.alert_service import AlertService

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = 1


class AlertController:
    """
    Handles all GUI interactions related to price alerts.

    USAGE IN GUI (Phase 8):
        self.ctrl = AlertController()

        # When user sets an alert:
        result = self.ctrl.create_alert(
            symbol='AAPL',
            condition='ABOVE',
            target_price=200.00
        )
    """

    def __init__(self, alert_service: AlertService = None):
        self.service = alert_service or AlertService()

    def create_alert(self, symbol: str, condition: str,
                     target_price: float = None,
                     percent_value: float = None,
                     message: str = None,
                     user_id: int = DEFAULT_USER_ID) -> dict:
        """
        Creates a new price alert.
        Called when user submits the Set Alert form.
        """
        # Validation
        valid_conditions = {'ABOVE', 'BELOW', 'PERCENT_CHANGE'}
        if condition.upper() not in valid_conditions:
            return {
                'success': False,
                'message': f"Condition must be one of: {valid_conditions}",
                'data':    None
            }

        if condition.upper() in ('ABOVE', 'BELOW') and not target_price:
            return {
                'success': False,
                'message': "Target price is required for ABOVE/BELOW alerts.",
                'data':    None
            }

        if condition.upper() == 'PERCENT_CHANGE' and not percent_value:
            return {
                'success': False,
                'message': "Percent value is required for PERCENT_CHANGE alerts.",
                'data':    None
            }

        alert_id = self.service.create_alert(
            user_id       = user_id,
            symbol        = symbol.upper(),
            condition     = condition.upper(),
            target_price  = target_price,
            percent_value = percent_value,
            message       = message,
        )

        if not alert_id:
            return {
                'success': False,
                'message': f"Failed to create alert for {symbol}. "
                           f"Make sure the stock exists.",
                'data':    None
            }

        return {
            'success': True,
            'message': f"Alert set for {symbol.upper()}.",
            'data':    {'alert_id': alert_id}
        }

    def get_alerts(self, user_id: int = DEFAULT_USER_ID) -> dict:
        """Returns all alerts for the current user."""
        alerts = self.service.get_user_alerts(user_id)
        data   = [a.to_dict() for a in alerts]
        return {
            'success': True,
            'data':    data,
            'count':   len(data),
            'message': f"{len(data)} alert(s) found."
        }

    def delete_alert(self, alert_id: int) -> dict:
        """
        Deletes an alert.
        Called when user clicks delete on an alert row.
        """
        success = self.service.delete_alert(alert_id)
        return {
            'success': success,
            'message': "Alert deleted." if success else "Failed to delete alert.",
            'data':    None
        }

    def check_alerts(self, current_prices: dict) -> dict:
        """
        Runs the alert engine against current prices.
        Called by the scheduler on every price refresh.
        Returns any alerts that were triggered.
        """
        triggered = self.service.check_alerts(current_prices)
        return {
            'success':   True,
            'data':      triggered,
            'count':     len(triggered),
            'message':   f"{len(triggered)} alert(s) triggered."
        }
