"""
gui/windows/dashboard_window.py
================================
Main dashboard view.
Loads stock cards immediately with placeholders,
then fetches live prices on a background thread
so the GUI never freezes.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QLineEdit, QPushButton,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from gui.widgets.stock_card_widget import StockCardWidget

logger = logging.getLogger(__name__)


class QuoteLoadThread(QThread):
    """
    Fetches live stock quotes in a background thread.

    WHY A BACKGROUND THREAD?
        get_current_quotes() calls Yahoo Finance with a
        0.15s sleep per symbol. For 8 symbols that's
        ~1.2 seconds of blocking time. Running this on
        the main GUI thread freezes the entire window.
        Moving it to a QThread keeps the GUI responsive —
        cards appear instantly with placeholder prices,
        then update silently once the fetch completes.
    """

    quotes_ready = pyqtSignal(dict)

    def __init__(self, symbols: list):
        super().__init__()
        self.symbols = symbols

    def run(self):
        try:
            from services.data_fetcher_service import DataFetcherService
            quotes = DataFetcherService().get_current_quotes(self.symbols)
            self.quotes_ready.emit(quotes)
        except Exception as e:
            logger.warning(f"Quote fetch thread failed: {e}")
            self.quotes_ready.emit({})


class DashboardWindow(QWidget):
    """
    The main dashboard view.
    Shows a search bar, summary metric cards, and
    a grid of watchlist stock cards with live prices.
    """

    stock_selected = pyqtSignal(str)

    WATCHLIST_SYMBOLS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN',
        'TSLA', 'NVDA', 'META', 'JPM'
    ]

    def __init__(self, stock_controller=None, parent=None):
        super().__init__(parent)
        self.stock_ctrl   = stock_controller
        self.stock_cards  = {}
        self.quote_thread = None
        self._setup_ui()
        self._load_data()

    # ── UI Construction ──────────────────────────────────────

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        # ── Header ──────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)

        title = QLabel("Market Dashboard")
        title.setStyleSheet(
            "color: #e6edf3; font-size: 24px; font-weight: bold;"
        )

        self.last_updated = QLabel("Loading...")
        self.last_updated.setStyleSheet(
            "color: #8b949e; font-size: 12px;"
        )

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
        refresh_btn.clicked.connect(self._load_data)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.last_updated)
        header.addWidget(refresh_btn)
        outer.addLayout(header)

        # ── Search Bar ──────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "🔍  Search stocks by symbol or company name..."
        )
        self.search_input.setFixedHeight(44)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 22px;
                padding: 0px 20px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #1f6feb;
                background-color: #0d1117;
            }
        """)
        self.search_input.returnPressed.connect(self._on_search)

        search_btn = QPushButton("Search")
        search_btn.setFixedSize(100, 44)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: white;
                border: none;
                border-radius: 22px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        search_btn.clicked.connect(self._on_search)

        search_row.addWidget(self.search_input)
        search_row.addWidget(search_btn)
        outer.addLayout(search_row)

        # ── Summary Metric Cards ─────────────────────────────
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(14)

        self.card_tracked = self._metric_card(
            "Stocks Tracked", "10", "#1f6feb", "📊"
        )
        self.card_market = self._metric_card(
            "Market Status", "OPEN", "#3fb950", "🟢"
        )
        self.card_gainer = self._metric_card(
            "Top Gainer Today", "—", "#3fb950", "▲"
        )
        self.card_loser = self._metric_card(
            "Top Loser Today", "—", "#f85149", "▼"
        )

        for card in [self.card_tracked, self.card_market,
                     self.card_gainer, self.card_loser]:
            metrics_row.addWidget(card)

        outer.addLayout(metrics_row)

        # ── Watchlist Section Header ─────────────────────────
        wl_header = QHBoxLayout()
        wl_title = QLabel("Watchlist")
        wl_title.setStyleSheet(
            "color: #e6edf3; font-size: 18px; font-weight: bold;"
        )
        wl_sub = QLabel("Click any card to view full analysis")
        wl_sub.setStyleSheet("color: #8b949e; font-size: 12px;")
        wl_header.addWidget(wl_title)
        wl_header.addStretch()
        wl_header.addWidget(wl_sub)
        outer.addLayout(wl_header)

        # ── Stock Cards Grid ─────────────────────────────────
        self.cards_widget = QWidget()
        self.cards_widget.setStyleSheet("background: transparent;")
        self.cards_layout = QGridLayout(self.cards_widget)
        self.cards_layout.setHorizontalSpacing(14)
        self.cards_layout.setVerticalSpacing(14)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        outer.addWidget(self.cards_widget)
        outer.addStretch()

    def _metric_card(self, title: str, value: str,
                      color: str, icon: str) -> QFrame:
        """Creates a summary metric card with icon."""
        card = QFrame()
        card.setFixedHeight(90)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {color};
            }}
        """)

        h = QHBoxLayout(card)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(14)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "background-color: transparent; font-size: 20px; border: none;"
        )

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        t = QLabel(title)
        t.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: bold; "
            "background: transparent; border: none;"
        )

        v = QLabel(value)
        v.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        card.value_label = v

        text_col.addWidget(t)
        text_col.addWidget(v)

        h.addWidget(icon_lbl)
        h.addLayout(text_col)
        h.addStretch()

        return card

    # ── Data Loading ─────────────────────────────────────────

    def _load_data(self):
        """Entry point for loading/refreshing all dashboard data."""
        from datetime import datetime
        self.last_updated.setText(
            f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        )
        self._populate_stock_cards()

    def _populate_stock_cards(self):
        """
        Builds stock cards immediately using DB metadata,
        then starts a background thread to fill in live prices.

        TWO-PHASE APPROACH:
            Phase 1 (instant): Create cards with company names
                               from the local database. Prices
                               show as "—" until the API responds.
            Phase 2 (~1 sec):  Background thread fetches live
                               prices and calls _on_quotes_ready()
                               which updates each card in place.
        """
        # Clear existing cards
        for i in reversed(range(self.cards_layout.count())):
            w = self.cards_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        self.stock_cards.clear()

        symbols   = self.WATCHLIST_SYMBOLS
        col_count = 4

        # Phase 1 — Build cards with DB info (fast, no network)
        for idx, symbol in enumerate(symbols):
            name = symbol
            if self.stock_ctrl:
                detail = self.stock_ctrl.get_stock_detail(symbol)
                if detail['success'] and detail['data']:
                    name = detail['data'].get('name', symbol)[:28]

            card = StockCardWidget(symbol, name, 0.0, 0.0, 0.0)
            card.clicked.connect(self.stock_selected.emit)

            row = idx // col_count
            col = idx  % col_count
            self.cards_layout.addWidget(card, row, col)
            self.stock_cards[symbol] = card

        # Phase 2 — Fetch live prices in the background
        if self.quote_thread and self.quote_thread.isRunning():
            self.quote_thread.quit()
            self.quote_thread.wait()

        self.quote_thread = QuoteLoadThread(symbols)
        self.quote_thread.quotes_ready.connect(self._on_quotes_ready)
        self.quote_thread.start()

    def _on_quotes_ready(self, live_prices: dict):
        """
        Called by QuoteLoadThread when live prices arrive.
        Updates each existing card in place — no grid rebuild,
        no flicker.
        """
        for symbol, card in self.stock_cards.items():
            price = float(live_prices.get(symbol, 0) or 0)
            if not price:
                continue

            change  = 0.0
            chg_pct = 0.0

            if self.stock_ctrl:
                pd_ = self.stock_ctrl.get_price_change(symbol)
                if pd_['success'] and pd_['data']:
                    prev = float(pd_['data'].get('prev_price') or 0)
                    if prev:
                        change  = round(price - prev, 2)
                        chg_pct = round((change / prev) * 100, 2)

            card.update_price(price, change, chg_pct)

        # Update top gainer and loser summary cards
        self._update_gainer_loser(live_prices)

    def _update_gainer_loser(self, live_prices: dict):
        """Updates the Top Gainer and Top Loser summary cards."""
        changes = {}
        for symbol in self.WATCHLIST_SYMBOLS:
            price = float(live_prices.get(symbol, 0) or 0)
            if not price or not self.stock_ctrl:
                continue
            pd_ = self.stock_ctrl.get_price_change(symbol)
            if pd_['success'] and pd_['data']:
                prev = float(pd_['data'].get('prev_price') or 0)
                if prev:
                    pct = round((price - prev) / prev * 100, 2)
                    changes[symbol] = pct

        if not changes:
            return

        top_gainer = max(changes, key=changes.get)
        top_loser  = min(changes, key=changes.get)

        gainer_pct = changes[top_gainer]
        loser_pct  = changes[top_loser]

        self.card_gainer.value_label.setText(
            f"{top_gainer}  +{gainer_pct:.2f}%"
        )
        self.card_loser.value_label.setText(
            f"{top_loser}  {loser_pct:.2f}%"
        )

    # ── Search ───────────────────────────────────────────────

    def _on_search(self):
        """Handles stock search bar submission."""
        query = self.search_input.text().strip()
        if not query or not self.stock_ctrl:
            return

        result = self.stock_ctrl.search(query)
        if result['success'] and result['data']:
            self.stock_selected.emit(result['data'][0]['symbol'])
        else:
            self.last_updated.setText(
                result.get('message', 'No results found.')
            )