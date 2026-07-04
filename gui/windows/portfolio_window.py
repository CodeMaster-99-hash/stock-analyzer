"""
gui/windows/portfolio_window.py
================================
Portfolio management view.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QHeaderView, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)

DEFAULT_PORTFOLIO_ID = 1


class PortfolioWindow(QWidget):

    def __init__(self, portfolio_controller=None,
                 data_fetcher=None, parent=None):
        super().__init__(parent)
        self.portfolio_ctrl = portfolio_controller
        self.data_fetcher   = data_fetcher
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        # ── Header ──────────────────────────────────────────
        header = QHBoxLayout()

        title = QLabel("Portfolio")
        title.setStyleSheet(
            "color: #e6edf3; font-size: 24px; font-weight: bold;"
        )

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setFixedSize(110, 38)
        refresh_btn.setStyleSheet(self._secondary_btn_style())
        refresh_btn.clicked.connect(self.refresh)

        add_btn = QPushButton("＋  Add Transaction")
        add_btn.setFixedSize(170, 38)
        add_btn.setStyleSheet(self._primary_btn_style())
        add_btn.clicked.connect(self._show_add_transaction)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(refresh_btn)
        header.addWidget(add_btn)
        outer.addLayout(header)

        # ── Summary Cards ───────────────────────────────────
        cards = QHBoxLayout()
        cards.setSpacing(14)

        self.invested_card = self._metric_card("Total Invested", "$0.00", "#e6edf3")
        self.value_card    = self._metric_card("Current Value",  "$0.00", "#e6edf3")
        self.pnl_card       = self._metric_card("Total P&L",      "$0.00", "#3fb950")
        self.pnl_pct_card   = self._metric_card("Return %",       "0.00%", "#3fb950")

        for c in [self.invested_card, self.value_card,
                  self.pnl_card, self.pnl_pct_card]:
            cards.addWidget(c)

        outer.addLayout(cards)

        # ── Tabs ─────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 8px;
                background-color: #161b22;
            }
            QTabBar::tab {
                background-color: #0d1117;
                color: #8b949e;
                padding: 10px 24px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #161b22;
                color: #e6edf3;
                border-bottom: 2px solid #1f6feb;
                font-weight: bold;
            }
            QTabBar::tab:hover { color: #e6edf3; }
        """)

        self.holdings_table = self._build_table([
            'Symbol', 'Name', 'Shares', 'Avg Cost',
            'Current', 'Value', 'P&L', 'P&L %', 'Sector'
        ])
        tabs.addTab(self.holdings_table, "Holdings")

        self.transactions_table = self._build_table([
            'Date', 'Symbol', 'Type', 'Shares', 'Price', 'Total', 'Notes'
        ])
        tabs.addTab(self.transactions_table, "Transaction History")

        outer.addWidget(tabs)

    def _metric_card(self, title: str, value: str, color: str) -> QFrame:
        """Creates a metric card with properly stacked title/value."""
        card = QFrame()
        card.setFixedHeight(86)
        card.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(6)

        t = QLabel(title)
        t.setFixedHeight(16)
        t.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: bold; "
            "background: transparent; border: none;"
        )

        val = QLabel(value)
        val.setFixedHeight(28)
        val.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        card.value_label = val

        v.addWidget(t)
        v.addWidget(val)
        v.addStretch()

        return card

    def _build_table(self, headers: list) -> QTableWidget:
        """Builds a styled table widget."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(400)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                border: none;
                gridline-color: #21262d;
                color: #e6edf3;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 10px;
                border: none;
            }
            QTableWidget::item:alternate {
                background-color: #0d1117;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #8b949e;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #30363d;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        return table

    def _primary_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388bfd; }
        """

    def _secondary_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #21262d;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #30363d; }
        """

    def refresh(self):
        self._load_holdings()
        self._load_transactions()

    def _load_holdings(self):
        if not self.portfolio_ctrl:
            return

        current_prices = {}
        if self.data_fetcher:
            symbols = ['AAPL','MSFT','GOOGL','AMZN',
                       'TSLA','NVDA','META','JPM','JNJ','V']
            try:
                current_prices = self.data_fetcher.get_current_quotes(symbols)
            except Exception as e:
                logger.warning(f"Price fetch failed: {e}")

        result = self.portfolio_ctrl.get_portfolio_summary(
            DEFAULT_PORTFOLIO_ID, current_prices
        )
        if not result['success']:
            return

        summary  = result['data']
        holdings = summary.get('holdings', [])

        invested = summary.get('total_invested', 0)
        value    = summary.get('current_value',  0)
        pnl      = summary.get('total_pnl',      0)
        pnl_pct  = summary.get('total_pnl_pct',  0)

        self.invested_card.value_label.setText(f"${invested:,.2f}")
        self.value_card.value_label.setText(f"${value:,.2f}")

        pnl_color = "#3fb950" if pnl >= 0 else "#f85149"
        self.pnl_card.value_label.setText(f"${pnl:,.2f}")
        self.pnl_card.value_label.setStyleSheet(
            f"color: {pnl_color}; font-size: 20px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        self.pnl_pct_card.value_label.setText(f"{pnl_pct:.2f}%")
        self.pnl_pct_card.value_label.setStyleSheet(
            f"color: {pnl_color}; font-size: 20px; font-weight: bold; "
            f"background: transparent; border: none;"
        )

        self.holdings_table.setRowCount(len(holdings))

        if not holdings:
            # Show empty state message inline as a single row
            self.holdings_table.setRowCount(1)
            empty_item = QTableWidgetItem(
                "No holdings yet — click 'Add Transaction' to get started."
            )
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setForeground(QColor("#8b949e"))
            self.holdings_table.setItem(0, 0, empty_item)
            self.holdings_table.setSpan(0, 0, 1, 9)
            return

        for row, h in enumerate(holdings):
            pnl_val = h.get('pnl', 0)
            color   = QColor("#3fb950") if pnl_val >= 0 else QColor("#f85149")

            values = [
                h.get('symbol',        ''),
                h.get('stock_name',    '')[:20],
                f"{h.get('shares', 0):.4f}",
                f"${h.get('avg_cost', 0):.2f}",
                f"${h.get('current_price', 0):.2f}",
                f"${h.get('market_value', 0):,.2f}",
                f"${pnl_val:,.2f}",
                f"{h.get('pnl_pct', 0):.2f}%",
                h.get('sector', '') or '',
            ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col in (6, 7):
                    item.setForeground(color)
                self.holdings_table.setItem(row, col, item)

    def _load_transactions(self):
        if not self.portfolio_ctrl:
            return

        result = self.portfolio_ctrl.get_transactions(DEFAULT_PORTFOLIO_ID)
        if not result['success']:
            return

        transactions = result['data']

        if not transactions:
            self.transactions_table.setRowCount(1)
            empty_item = QTableWidgetItem(
                "No transactions recorded yet."
            )
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setForeground(QColor("#8b949e"))
            self.transactions_table.setItem(0, 0, empty_item)
            self.transactions_table.setSpan(0, 0, 1, 7)
            return

        self.transactions_table.setRowCount(len(transactions))

        for row, t in enumerate(transactions):
            t_type = t.get('type', '')
            color  = QColor("#3fb950") if t_type == 'BUY' else QColor("#f85149")
            total  = float(t.get('quantity', 0)) * float(t.get('price', 0))
            date   = str(t.get('trans_date', ''))[:10]

            values = [
                date,
                t.get('symbol', ''),
                t_type,
                f"{float(t.get('quantity', 0)):.4f}",
                f"${float(t.get('price', 0)):.2f}",
                f"${total:,.2f}",
                t.get('notes', '') or '',
            ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 2:
                    item.setForeground(color)
                self.transactions_table.setItem(row, col, item)

    def _show_add_transaction(self):
        from gui.dialogs.add_transaction_dialog import AddTransactionDialog
        dialog = AddTransactionDialog(
            portfolio_controller=self.portfolio_ctrl,
            parent=self
        )
        if dialog.exec():
            self.refresh()