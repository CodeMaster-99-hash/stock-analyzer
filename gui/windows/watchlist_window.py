"""
gui/windows/watchlist_window.py
================================
Watchlist management view.
Loads static info instantly from DB, then fetches
live prices on a background thread to avoid UI freezing.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class WatchlistWindow(QWidget):
    """Displays and manages the user's watchlist."""

    stock_selected = pyqtSignal(str)

    SYMBOLS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN',
        'TSLA', 'NVDA', 'META', 'JPM', 'JNJ', 'V'
    ]

    def __init__(self, stock_controller=None,
                 data_fetcher=None, parent=None):
        super().__init__(parent)
        self.stock_ctrl   = stock_controller
        self.data_fetcher = data_fetcher
        self.quote_thread = None
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        header = QHBoxLayout()

        title = QLabel("Watchlist")
        title.setStyleSheet(
            "color: #e6edf3; font-size: 24px; font-weight: bold;"
        )

        self.status_label = QLabel("Loading...")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setFixedSize(110, 36)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        refresh_btn.clicked.connect(self.refresh)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_label)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # ── Hint label ───────────────────────────────────────
        hint = QLabel("Double-click any row to view the full chart analysis.")
        hint.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(hint)

        # ── Table ─────────────────────────────────────────────
        headers = [
            'Symbol', 'Company', 'Price', 'Change',
            'Change %', 'Volume', 'Sector', 'Action'
        ]
        self.table = QTableWidget()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(400)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
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
        layout.addWidget(self.table)

    # ── Data Loading ──────────────────────────────────────────

    def refresh(self):
        """
        Two-phase refresh:
        Phase 1 — Fill static info (name, sector) from DB instantly.
        Phase 2 — Fetch live prices on a background thread,
                  then update price columns without rebuilding the table.
        """
        symbols = self.SYMBOLS
        self.table.setRowCount(len(symbols))
        self.status_label.setText("Loading...")

        # Phase 1 — Populate static columns from local DB (fast)
        for row, symbol in enumerate(symbols):
            name   = symbol
            sector = ''

            if self.stock_ctrl:
                detail = self.stock_ctrl.get_stock_detail(symbol)
                if detail['success'] and detail['data']:
                    d      = detail['data']
                    name   = d.get('name', symbol)[:30]
                    sector = d.get('sector', '') or ''

            row_values = [
                symbol,
                name,
                "Loading...",   # price — filled in by background thread
                "—",            # change
                "—",            # change %
                "—",            # volume
                sector,
                "View Chart",
            ]

            for col, val in enumerate(row_values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        # Phase 2 — Fetch live prices on background thread
        if self.quote_thread and self.quote_thread.isRunning():
            self.quote_thread.quit()
            self.quote_thread.wait()

        from gui.windows.dashboard_window import QuoteLoadThread
        self.quote_thread = QuoteLoadThread(symbols)
        self.quote_thread.quotes_ready.connect(self._on_quotes_ready)
        self.quote_thread.start()

    def _on_quotes_ready(self, live_prices: dict):
        """
        Called when the background quote thread finishes.
        Updates only the price-related columns — no table rebuild.
        """
        from datetime import datetime
        self.status_label.setText(
            f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        )

        for row in range(self.table.rowCount()):
            symbol_item = self.table.item(row, 0)
            if not symbol_item:
                continue

            symbol = symbol_item.text()
            price  = float(live_prices.get(symbol, 0) or 0)

            change  = 0.0
            chg_pct = 0.0

            if self.stock_ctrl:
                pd_ = self.stock_ctrl.get_price_change(symbol)
                if pd_['success'] and pd_['data']:
                    prev = float(pd_['data'].get('prev_price') or 0)
                    if prev and price:
                        change  = round(price - prev, 2)
                        chg_pct = round((change / prev) * 100, 2)

            color  = (QColor("#3fb950") if change >= 0
                      else QColor("#f85149"))
            prefix = "▲" if change > 0 else "▼" if change < 0 else "●"

            # Update price, change, change % columns
            price_item = QTableWidgetItem(
                f"${price:.2f}" if price else "—"
            )
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, price_item)

            change_item = QTableWidgetItem(
                f"{prefix} {abs(change):.2f}"
            )
            change_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            change_item.setForeground(color)
            self.table.setItem(row, 3, change_item)

            pct_item = QTableWidgetItem(f"{abs(chg_pct):.2f}%")
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pct_item.setForeground(color)
            self.table.setItem(row, 4, pct_item)

    def _on_row_double_clicked(self, index):
        """Emits stock_selected when a row is double-clicked."""
        row    = index.row()
        symbol_item = self.table.item(row, 0)
        if symbol_item:
            self.stock_selected.emit(symbol_item.text())