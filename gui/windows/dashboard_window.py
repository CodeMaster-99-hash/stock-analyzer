"""
gui/windows/dashboard_window.py
================================
Main dashboard with dynamic real-time stock search.

Supports searching ANY stock globally via Yahoo Finance.

Two-phase card loading:
    1. Cards appear instantly.
    2. Prices load asynchronously.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QLineEdit,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
)

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QThread,
    QTimer,
)

from PyQt6.QtGui import QColor

from gui.widgets.stock_card_widget import StockCardWidget


logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Background Threads
# ══════════════════════════════════════════════════════════════


class QuoteLoadThread(QThread):
    """
    Fetches live quotes in a background thread.

    Prevents the dashboard from freezing while waiting
    for sequential API calls.
    """

    quotes_ready = pyqtSignal(dict)

    def __init__(self, symbols: list):
        super().__init__()
        self.symbols = symbols

    def run(self):
        try:
            from services.data_fetcher_service import (
                DataFetcherService
            )

            quotes = (
                DataFetcherService()
                .get_current_quotes(self.symbols)
            )

            self.quotes_ready.emit(quotes)

        except Exception as e:
            logger.warning(
                f"Quote thread failed: {e}"
            )

            self.quotes_ready.emit({})


class SearchThread(QThread):
    """
    Runs global stock search in the background.

    Searches both local DB and Yahoo Finance globally.
    Prevents the search bar from freezing during API calls.
    """

    results_ready = pyqtSignal(list)

    def __init__(
        self,
        query: str,
        stock_controller
    ):
        super().__init__()

        self.query = query
        self.ctrl = stock_controller

    def run(self):
        try:
            result = self.ctrl.search_global(
                self.query
            )

            data = result.get("data", []) or []

            self.results_ready.emit(data)

        except Exception as e:
            logger.warning(
                f"Search thread failed: {e}"
            )

            self.results_ready.emit([])


class FetchStockThread(QThread):
    """
    Fetches a new stock from Yahoo Finance in background.

    Called when user selects a stock not yet in the database.

    Saves stock information and one year of price history
    to MySQL.
    """

    fetch_done = pyqtSignal(dict)

    def __init__(
        self,
        symbol: str,
        stock_controller
    ):
        super().__init__()

        self.symbol = symbol
        self.ctrl = stock_controller

    def run(self):
        try:
            result = self.ctrl.fetch_and_load_stock(
                self.symbol
            )

            self.fetch_done.emit(result)

        except Exception as e:
            logger.warning(
                f"Fetch thread failed: {e}"
            )

            self.fetch_done.emit(
                {
                    "success": False,
                    "message": str(e),
                }
            )


# ══════════════════════════════════════════════════════════════
# Dashboard Window
# ══════════════════════════════════════════════════════════════


class DashboardWindow(QWidget):
    """
    Main dashboard view.

    Features:
        - Dynamic global stock search with debounce
        - Real-time price cards with async loading
        - DB fallback when Yahoo Finance is rate-limited
        - Top gainer / loser metric cards
        - Click any card to navigate to charts
    """

    stock_selected = pyqtSignal(str)

    WATCHLIST_SYMBOLS = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "JPM",
    ]

    def __init__(
        self,
        stock_controller=None,
        parent=None
    ):
        super().__init__(parent)

        self.stock_ctrl = stock_controller
        self.stock_cards = {}

        self.quote_thread = None
        self.search_thread = None
        self.fetch_thread = None

        # Debounce timer.
        # Waits 400ms after the user stops typing
        # before firing the search.
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(
            self._run_search
        )

        self._setup_ui()
        self._load_data()

    # ──────────────────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        outer = QVBoxLayout(self)

        outer.setContentsMargins(
            32,
            28,
            32,
            28
        )

        outer.setSpacing(18)

        # ── Header ────────────────────────────────────────────

        header = QHBoxLayout()
        header.setSpacing(12)

        title = QLabel("Market Dashboard")

        title.setStyleSheet(
            "color: #e6edf3; "
            "font-size: 24px; "
            "font-weight: bold;"
        )

        self.last_updated = QLabel(
            "Loading..."
        )

        self.last_updated.setStyleSheet(
            "color: #8b949e; "
            "font-size: 12px;"
        )

        refresh_btn = QPushButton(
            "⟳  Refresh"
        )

        refresh_btn.setFixedSize(
            110,
            36
        )

        refresh_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #388bfd;
            }

            QPushButton:pressed {
                background-color: #1158c7;
            }
            """
        )

        refresh_btn.clicked.connect(
            self._load_data
        )

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.last_updated)
        header.addWidget(refresh_btn)

        outer.addLayout(header)

        # ── Search Bar with Live Dropdown ─────────────────────

        search_container = QWidget()

        search_container.setStyleSheet(
            "background: transparent;"
        )

        search_vbox = QVBoxLayout(
            search_container
        )

        search_vbox.setContentsMargins(
            0,
            0,
            0,
            0
        )

        search_vbox.setSpacing(0)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "🔍  Search any stock — AAPL, Tesla, "
            "Reliance, BTC-USD, Gold ETF..."
        )

        self.search_input.setFixedHeight(46)

        self.search_input.setStyleSheet(
            """
            QLineEdit {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 23px;
                padding: 0px 20px;
                font-size: 14px;
            }

            QLineEdit:focus {
                border-color: #1f6feb;
                background-color: #0d1117;
            }
            """
        )

        self.search_input.textChanged.connect(
            self._on_search_text_changed
        )

        self.search_input.returnPressed.connect(
            self._run_search
        )

        clear_btn = QPushButton("✕")

        clear_btn.setFixedSize(
            46,
            46
        )

        clear_btn.setToolTip(
            "Clear search"
        )

        clear_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 23px;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #30363d;
                color: #e6edf3;
            }
            """
        )

        clear_btn.clicked.connect(
            self._clear_search
        )

        search_row.addWidget(
            self.search_input
        )

        search_row.addWidget(
            clear_btn
        )

        search_vbox.addLayout(
            search_row
        )

        # ── Search Results Dropdown ───────────────────────────

        self.search_results = QListWidget()

        self.search_results.setVisible(
            False
        )

        self.search_results.setMaximumHeight(
            300
        )

        self.search_results.setStyleSheet(
            """
            QListWidget {
                background-color: #161b22;
                border: 1px solid #1f6feb;
                border-top: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                color: #e6edf3;
                font-size: 13px;
                outline: none;
            }

            QListWidget::item {
                padding: 10px 20px;
                border-bottom: 1px solid #21262d;
            }

            QListWidget::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }

            QListWidget::item:hover {
                background-color: #21262d;
            }
            """
        )

        self.search_results.itemClicked.connect(
            self._on_result_clicked
        )

        search_vbox.addWidget(
            self.search_results
        )

        # ── Search Status ─────────────────────────────────────

        self.search_status = QLabel("")

        self.search_status.setStyleSheet(
            "color: #8b949e; "
            "font-size: 11px; "
            "padding: 4px 20px;"
        )

        self.search_status.setVisible(
            False
        )

        search_vbox.addWidget(
            self.search_status
        )

        outer.addWidget(
            search_container
        )

        # ── Summary Metric Cards ──────────────────────────────

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(14)

        self.card_tracked = self._metric_card(
            "Stocks in DB",
            "—",
            "#1f6feb",
            "📊"
        )

        self.card_market = self._metric_card(
            "Market Status",
            "OPEN",
            "#3fb950",
            "🟢"
        )

        self.card_gainer = self._metric_card(
            "Top Gainer Today",
            "—",
            "#3fb950",
            "▲"
        )

        self.card_loser = self._metric_card(
            "Top Loser Today",
            "—",
            "#f85149",
            "▼"
        )

        for card in [
            self.card_tracked,
            self.card_market,
            self.card_gainer,
            self.card_loser,
        ]:
            metrics_row.addWidget(card)

        outer.addLayout(
            metrics_row
        )

        # ── Watchlist Section Header ──────────────────────────

        wl_header = QHBoxLayout()

        wl_title = QLabel(
            "Watchlist"
        )

        wl_title.setStyleSheet(
            "color: #e6edf3; "
            "font-size: 18px; "
            "font-weight: bold;"
        )

        wl_hint = QLabel(
            "Click card to view charts  ·  "
            "Search above to add any global stock"
        )

        wl_hint.setStyleSheet(
            "color: #8b949e; "
            "font-size: 11px;"
        )

        wl_header.addWidget(
            wl_title
        )

        wl_header.addStretch()

        wl_header.addWidget(
            wl_hint
        )

        outer.addLayout(
            wl_header
        )

        # ── Stock Cards Grid ──────────────────────────────────

        self.cards_widget = QWidget()

        self.cards_widget.setStyleSheet(
            "background: transparent;"
        )

        self.cards_layout = QGridLayout(
            self.cards_widget
        )

        self.cards_layout.setHorizontalSpacing(
            14
        )

        self.cards_layout.setVerticalSpacing(
            14
        )

        self.cards_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        outer.addWidget(
            self.cards_widget
        )

        outer.addStretch()

    def _metric_card(
        self,
        title: str,
        value: str,
        color: str,
        icon: str
    ) -> QFrame:
        """Creates a summary metric card with icon."""

        card = QFrame()

        card.setFixedHeight(
            90
        )

        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }}

            QFrame:hover {{
                border-color: {color};
            }}
            """
        )

        h = QHBoxLayout(card)

        h.setContentsMargins(
            16,
            0,
            16,
            0
        )

        h.setSpacing(14)

        icon_lbl = QLabel(icon)

        icon_lbl.setFixedSize(
            36,
            36
        )

        icon_lbl.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        icon_lbl.setStyleSheet(
            "background: transparent; "
            "font-size: 20px; "
            "border: none;"
        )

        text_col = QVBoxLayout()

        text_col.setSpacing(2)

        title_label = QLabel(title)

        title_label.setStyleSheet(
            "color: #8b949e; "
            "font-size: 11px; "
            "font-weight: bold; "
            "background: transparent; "
            "border: none;"
        )

        value_label = QLabel(value)

        value_label.setStyleSheet(
            f"color: {color}; "
            "font-size: 22px; "
            "font-weight: bold; "
            "background: transparent; "
            "border: none;"
        )

        card.value_label = value_label

        text_col.addWidget(
            title_label
        )

        text_col.addWidget(
            value_label
        )

        h.addWidget(
            icon_lbl
        )

        h.addLayout(
            text_col
        )

        h.addStretch()

        return card

    # ──────────────────────────────────────────────────────────
    # Data Loading
    # ──────────────────────────────────────────────────────────

    def _load_data(self):
        """Entry point for loading / refreshing dashboard data."""

        from datetime import datetime

        self.last_updated.setText(
            f"Updated: "
            f"{datetime.now().strftime('%H:%M:%S')}"
        )

        self._update_stock_count()
        self._populate_stock_cards()

    def _update_stock_count(self):
        """Updates the 'Stocks in DB' metric card."""

        try:
            from database.connection import (
                DatabaseConnection
            )

            conn = (
                DatabaseConnection
                .get_connection()
            )

            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM stocks"
            )

            count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            self.card_tracked.value_label.setText(
                str(count)
            )

        except Exception:
            self.card_tracked.value_label.setText(
                "—"
            )

    def _populate_stock_cards(self):
        """
        Two-phase card loading.

        Phase 1:
            Build cards from local DB metadata.
            Prices show as placeholders.

        Phase 2:
            QuoteLoadThread fetches live prices
            asynchronously.
        """

        # Clear old cards
        for i in reversed(
            range(self.cards_layout.count())
        ):
            widget = (
                self.cards_layout
                .itemAt(i)
                .widget()
            )

            if widget:
                widget.setParent(None)

        self.stock_cards.clear()

        symbols = self.WATCHLIST_SYMBOLS
        col_count = 4

        # Phase 1 — Build cards immediately
        for idx, symbol in enumerate(symbols):

            name = symbol

            if self.stock_ctrl:

                detail = (
                    self.stock_ctrl
                    .get_stock_detail(symbol)
                )

                if (
                    detail["success"]
                    and detail["data"]
                ):
                    name = (
                        detail["data"]
                        .get("name", symbol)
                    )[:28]

            card = StockCardWidget(
                symbol,
                name,
                0.0,
                0.0,
                0.0
            )

            card.clicked.connect(
                self._on_card_clicked
            )

            row = idx // col_count
            col = idx % col_count

            self.cards_layout.addWidget(
                card,
                row,
                col
            )

            self.stock_cards[symbol] = card

        # Phase 2 — Fetch live prices
        if (
            self.quote_thread
            and self.quote_thread.isRunning()
        ):
            self.quote_thread.quit()
            self.quote_thread.wait()

        self.quote_thread = QuoteLoadThread(
            symbols
        )

        self.quote_thread.quotes_ready.connect(
            self._on_quotes_ready
        )

        self.quote_thread.start()

    def _on_card_clicked(
        self,
        symbol: str
    ):
        """Navigate to charts when a stock card is clicked."""

        self._clear_search()

        self.stock_selected.emit(
            symbol
        )

    def _on_quotes_ready(
        self,
        live_prices: dict
    ):
        """
        Called when background quote thread finishes.

        Updates each card in place.

        Falls back to latest DB closing price if
        live fetch returns empty.
        """

        if not live_prices:
            live_prices = (
                self._get_db_prices()
            )

        for symbol, card in self.stock_cards.items():

            price = float(
                live_prices.get(
                    symbol,
                    0
                ) or 0
            )

            if not price:
                continue

            change = 0.0
            change_pct = 0.0

            if self.stock_ctrl:

                price_data = (
                    self.stock_ctrl
                    .get_price_change(symbol)
                )

                if (
                    price_data["success"]
                    and price_data["data"]
                ):
                    prev = float(
                        price_data["data"]
                        .get("prev_price") or 0
                    )

                    if prev:
                        change = round(
                            price - prev,
                            2
                        )

                        change_pct = round(
                            (change / prev) * 100,
                            2
                        )

            card.update_price(
                price,
                change,
                change_pct
            )

        self._update_gainer_loser(
            live_prices
        )

    def _get_db_prices(self) -> dict:
        """
        Fallback that retrieves latest closing prices
        directly from MySQL when Yahoo Finance is
        rate-limiting live quote requests.
        """

        prices = {}

        try:
            from database.connection import (
                DatabaseConnection
            )

            conn = (
                DatabaseConnection
                .get_connection()
            )

            cursor = conn.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT s.symbol, hp.close_price
                FROM stocks s
                JOIN historical_prices hp
                    ON s.id = hp.stock_id
                WHERE hp.price_date = (
                    SELECT MAX(price_date)
                    FROM historical_prices
                    WHERE stock_id = s.id
                )
                ORDER BY s.symbol
                """
            )

            for row in cursor.fetchall():
                prices[row["symbol"]] = float(
                    row["close_price"]
                )

            cursor.close()
            conn.close()

            logger.info(
                f"DB price fallback: "
                f"loaded {len(prices)} prices"
            )

        except Exception as e:
            logger.error(
                f"DB price fallback failed: {e}"
            )

        return prices

    def _update_gainer_loser(
        self,
        live_prices: dict
    ):
        """Updates Top Gainer and Top Loser metric cards."""

        changes = {}

        for symbol in self.WATCHLIST_SYMBOLS:

            price = float(
                live_prices.get(
                    symbol,
                    0
                ) or 0
            )

            if not price or not self.stock_ctrl:
                continue

            price_data = (
                self.stock_ctrl
                .get_price_change(symbol)
            )

            if (
                price_data["success"]
                and price_data["data"]
            ):
                prev = float(
                    price_data["data"]
                    .get("prev_price") or 0
                )

                if prev:
                    changes[symbol] = round(
                        (price - prev)
                        / prev
                        * 100,
                        2
                    )

        if not changes:
            return

        top_gainer = max(
            changes,
            key=changes.get
        )

        top_loser = min(
            changes,
            key=changes.get
        )

        self.card_gainer.value_label.setText(
            f"{top_gainer}  "
            f"+{changes[top_gainer]:.2f}%"
        )

        self.card_loser.value_label.setText(
            f"{top_loser}  "
            f"{changes[top_loser]:.2f}%"
        )

    # ──────────────────────────────────────────────────────────
    # Search Logic
    # ──────────────────────────────────────────────────────────

    def _on_search_text_changed(
        self,
        text: str
    ):
        """
        Called on every keystroke.

        Uses a 400ms debounce timer.
        """

        text = text.strip()

        if not text:
            self._clear_search()
            return

        if len(text) < 2:
            self.search_results.setVisible(
                False
            )

            self.search_status.setVisible(
                False
            )

            return

        # Reset debounce timer
        self.search_timer.stop()
        self.search_timer.start(400)

        self.search_status.setText(
            "Searching..."
        )

        self.search_status.setVisible(
            True
        )

    def _run_search(self):
        """
        Fires the actual search after debounce.

        Runs in a background SearchThread
        to keep GUI responsive.
        """

        query = (
            self.search_input
            .text()
            .strip()
        )

        if (
            not query
            or len(query) < 2
            or not self.stock_ctrl
        ):
            return

        # Cancel running search
        if (
            self.search_thread
            and self.search_thread.isRunning()
        ):
            self.search_thread.quit()
            self.search_thread.wait()

        self.search_thread = SearchThread(
            query,
            self.stock_ctrl
        )

        self.search_thread.results_ready.connect(
            self._on_search_results
        )

        self.search_thread.start()

    def _on_search_results(
        self,
        results: list
    ):
        """Populates the dropdown with search results."""

        self.search_results.clear()

        if not results:
            self.search_status.setText(
                "No results found. "
                "Try the exact ticker symbol."
            )

            self.search_results.setVisible(
                False
            )

            return

        self.search_status.setText(
            f"{len(results)} results  ·  "
            f"✓ = already saved  ·  "
            f"+ = click to add"
        )

        for result in results:

            symbol = result.get(
                "symbol",
                ""
            )

            name = result.get(
                "name",
                ""
            )[:38]

            exchange = result.get(
                "exchange",
                ""
            )

            quote_type = result.get(
                "type",
                "EQUITY"
            )

            in_db = result.get(
                "in_database",
                False
            )

            # Display badge
            badge = (
                "✓"
                if in_db
                else "+"
            )

            type_label = {
                "EQUITY": "📈",
                "ETF": "📊",
                "CRYPTOCURRENCY": "₿",
                "CURRENCY": "💱",
                "INDEX": "📉",
                "FUTURE": "📦",
            }.get(
                quote_type,
                "📈"
            )

            display = (
                f"{type_label}  "
                f"{symbol} {badge}  —  "
                f"{name}  "
                f"[{exchange}]"
            )

            item = QListWidgetItem(
                display
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                result
            )

            # Color coding
            if in_db:
                item.setForeground(
                    QColor("#3fb950")
                )

            elif quote_type == "CRYPTOCURRENCY":
                item.setForeground(
                    QColor("#bc8cff")
                )

            elif quote_type == "ETF":
                item.setForeground(
                    QColor("#e3b341")
                )

            else:
                item.setForeground(
                    QColor("#e6edf3")
                )

            self.search_results.addItem(
                item
            )

        self.search_results.setVisible(
            True
        )

    def _on_result_clicked(
        self,
        item: QListWidgetItem
    ):
        """
        Called when user clicks a search result.

        ✓ Stock already in DB:
            Navigate directly to charts.

        + New stock:
            Fetch from Yahoo Finance,
            save to MySQL,
            then navigate to charts.
        """

        data = item.data(
            Qt.ItemDataRole.UserRole
        )

        symbol = data.get(
            "symbol",
            ""
        )

        in_db = data.get(
            "in_database",
            False
        )

        if not symbol:
            return

        if in_db:

            self._clear_search()

            self.stock_selected.emit(
                symbol
            )

        else:

            self._fetch_new_stock(
                symbol,
                data.get(
                    "name",
                    symbol
                )
            )

    def _fetch_new_stock(
        self,
        symbol: str,
        name: str
    ):
        """
        Fetches a brand new stock from Yahoo Finance.

        Shows status feedback during the fetch.

        On success, navigates to charts.
        """

        self.search_status.setText(
            f"⏳  Fetching {symbol} "
            f"({name}) from Yahoo Finance..."
        )

        self.search_results.setVisible(
            False
        )

        if (
            self.fetch_thread
            and self.fetch_thread.isRunning()
        ):
            self.fetch_thread.quit()
            self.fetch_thread.wait()

        self.fetch_thread = FetchStockThread(
            symbol,
            self.stock_ctrl
        )

        self.fetch_thread.fetch_done.connect(
            lambda result, sym=symbol:
                self._on_stock_fetched(
                    sym,
                    result
                )
        )

        self.fetch_thread.start()

    def _on_stock_fetched(
        self,
        symbol: str,
        result: dict
    ):
        """Called when the new stock fetch thread completes."""

        if result.get("success"):

            fetched_name = (
                result.get(
                    "data",
                    {}
                ).get(
                    "name",
                    ""
                )
                if isinstance(
                    result.get("data"),
                    dict
                )
                else ""
            ) or symbol

            self.search_status.setText(
                f"✅  {fetched_name} "
                f"added to database successfully."
            )

            # Navigate to charts
            self._clear_search()

            self.stock_selected.emit(
                symbol
            )

        else:

            message = result.get(
                "message",
                "Unknown error"
            )

            self.search_status.setText(
                f"❌  Could not load "
                f"{symbol}: {message}"
            )

            logger.warning(
                f"Failed to fetch "
                f"{symbol}: {message}"
            )

    def _clear_search(self):
        """Clears search bar, hides dropdown and status."""

        self.search_timer.stop()

        self.search_input.clear()

        self.search_results.clear()

        self.search_results.setVisible(
            False
        )

        self.search_status.setVisible(
            False
        )