"""
gui/windows/chart_window.py
=============================
Full stock analysis view with price chart,
technical indicators, AI prediction, and details panel.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QFrame, QGridLayout,
    QComboBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from gui.widgets.chart_widget import ChartWidget

logger = logging.getLogger(__name__)


class DataLoadThread(QThread):
    """Loads and processes stock data in a background thread."""

    data_ready   = pyqtSignal(object, str)
    error_signal = pyqtSignal(str)

    def __init__(self, symbol: str, analytics_service):
        super().__init__()
        self.symbol    = symbol
        self.analytics = analytics_service

    def run(self):
        try:
            df = self.analytics.get_enriched_data(self.symbol, 365)
            self.data_ready.emit(df, self.symbol)
        except Exception as e:
            self.error_signal.emit(str(e))


class ChartWindow(QWidget):
    """Full stock analysis view."""

    def __init__(self, analytics_service=None,
                 stock_controller=None, parent=None):
        super().__init__(parent)
        self.analytics    = analytics_service
        self.stock_ctrl   = stock_controller
        self.current_df   = None
        self.current_sym  = ""
        self.load_thread  = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        header = QHBoxLayout()

        label = QLabel("Stock:")
        label.setStyleSheet("color: #8b949e; font-size: 13px;")

        self.stock_selector = QComboBox()
        self.stock_selector.setFixedWidth(160)
        self.stock_selector.setFixedHeight(36)
        self.stock_selector.addItems([
            'AAPL', 'MSFT', 'GOOGL', 'AMZN',
            'TSLA', 'NVDA', 'META', 'JPM', 'JNJ', 'V'
        ])
        self.stock_selector.setStyleSheet("""
            QComboBox {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background-color: #161b22;
                color: #e6edf3;
                selection-background-color: #1f6feb;
            }
        """)
        self.stock_selector.currentTextChanged.connect(self.load_stock)

        self.status_label = QLabel("Select a stock to view charts")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")

        header.addWidget(label)
        header.addWidget(self.stock_selector)
        header.addSpacing(16)
        header.addWidget(self.status_label)
        header.addStretch()
        layout.addLayout(header)

        # ── Main content split ───────────────────────────────
        content = QHBoxLayout()
        content.setSpacing(16)

        chart_section = QVBoxLayout()

        self.chart_tabs = QTabWidget()
        self.chart_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 8px;
                background-color: #161b22;
            }
            QTabBar::tab {
                background-color: #0d1117;
                color: #8b949e;
                padding: 8px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #161b22;
                color: #e6edf3;
                border-bottom: 2px solid #1f6feb;
                font-weight: bold;
            }
        """)

        self.price_chart = ChartWidget()
        self.chart_tabs.addTab(self.price_chart, "Price")

        self.rsi_chart = ChartWidget()
        self.chart_tabs.addTab(self.rsi_chart, "RSI")

        self.macd_chart = ChartWidget()
        self.chart_tabs.addTab(self.macd_chart, "MACD")

        chart_section.addWidget(self.chart_tabs)
        content.addLayout(chart_section, stretch=7)

        self.indicator_panel = self._build_indicator_panel()
        content.addWidget(self.indicator_panel, stretch=3)

        layout.addLayout(content)

    def _build_indicator_panel(self) -> QScrollArea:
        """Builds the right-side panel."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumWidth(300)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 8, 0)

        self.info_card        = self._make_panel_card("Stock Info")
        self.price_card       = self._make_panel_card("Price Summary")
        self.indicators_card  = self._make_panel_card("Indicators")
        self.prediction_card  = self._make_panel_card("AI Prediction")

        layout.addWidget(self.info_card)
        layout.addWidget(self.price_card)
        layout.addWidget(self.indicators_card)
        layout.addWidget(self.prediction_card)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _make_panel_card(self, title: str) -> QFrame:
        """Creates a labeled card for the side panel."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }
        """)

        v_layout = QVBoxLayout(card)
        v_layout.setSpacing(8)
        v_layout.setContentsMargins(16, 14, 16, 14)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        v_layout.addWidget(title_lbl)

        grid = QGridLayout()
        grid.setSpacing(6)
        v_layout.addLayout(grid)

        card.grid = grid
        card.rows = {}

        return card

    def _update_panel_card(self, card: QFrame, data: dict):
        """Fills a panel card with key-value rows."""
        for row_widgets in card.rows.values():
            for w in row_widgets:
                w.deleteLater()
        card.rows.clear()

        row_idx = 0
        for key, value in data.items():
            if value is None:
                continue

            key_lbl = QLabel(str(key))
            key_lbl.setStyleSheet(
                "color: #8b949e; font-size: 11px; "
                "background: transparent; border: none;"
            )

            val_lbl = QLabel(str(value))
            val_lbl.setWordWrap(True)
            val_lbl.setStyleSheet(
                "color: #e6edf3; font-size: 11px; font-weight: bold; "
                "background: transparent; border: none;"
            )
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

            card.grid.addWidget(key_lbl, row_idx, 0)
            card.grid.addWidget(val_lbl, row_idx, 1)
            card.rows[key] = [key_lbl, val_lbl]
            row_idx += 1

    def load_stock(self, symbol: str):
        """Loads and displays data for a symbol."""
        if not symbol or not self.analytics:
            return

        self.current_sym = symbol
        self.status_label.setText(f"Loading {symbol}...")

        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.quit()
            self.load_thread.wait()

        self.load_thread = DataLoadThread(symbol, self.analytics)
        self.load_thread.data_ready.connect(self._on_data_ready)
        self.load_thread.error_signal.connect(self._on_error)
        self.load_thread.start()

    def _on_data_ready(self, df, symbol: str):
        """Called when background thread finishes loading."""
        self.current_df = df
        self.status_label.setText(
            f"{symbol} — {len(df)} trading days loaded"
        )

        self.price_chart.plot_price_chart(df, symbol)
        self.rsi_chart.plot_rsi_chart(df, symbol)
        self.macd_chart.plot_macd_chart(df, symbol)

        # ── Stock Info card ───────────────────────────────────
        # Populated from the stock controller (company metadata),
        # independent of whether price history exists, so it
        # always has a chance to show something useful.
        if self.stock_ctrl:
            detail = self.stock_ctrl.get_stock_detail(symbol)
            if detail['success'] and detail['data']:
                d = detail['data']
                self._update_panel_card(self.info_card, {
                    'Name':     d.get('name') or symbol,
                    'Sector':   d.get('sector') or '—',
                    'Industry': d.get('industry') or '—',
                    'Exchange': d.get('exchange') or '—',
                    'Currency': d.get('currency') or 'USD',
                })
            else:
                self._update_panel_card(self.info_card, {
                    'Status': 'Stock details not in database'
                })
        else:
            self._update_panel_card(self.info_card, {
                'Status': 'Stock controller unavailable'
            })

        if df.empty:
            self._update_panel_card(self.price_card, {
                'Status': 'No price history available'
            })
            self._update_panel_card(self.indicators_card, {
                'Status': 'No indicator data available'
            })
            self._update_panel_card(self.prediction_card, {
                'Status': 'No data to predict from'
            })
            return

        latest = df.iloc[-1]

        # ── Price Summary card ─────────────────────────────────
        self._update_panel_card(self.price_card, {
            'Current':    f"${float(latest['close']):.2f}",
            '52W High':   f"${df['close'].max():.2f}",
            '52W Low':    f"${df['close'].min():.2f}",
            'Avg Volume': f"{int(df['volume'].mean()):,}",
        })

        # ── Indicators card ────────────────────────────────────
        indicators = {}
        if 'rsi_14' in df.columns and latest.get('rsi_14') is not None:
            rsi = float(latest['rsi_14'])
            tag = '⚠ OB' if rsi > 70 else '⚠ OS' if rsi < 30 else ''
            indicators['RSI (14)'] = f"{rsi:.1f} {tag}"
        if 'macd' in df.columns:
            indicators['MACD'] = f"{float(latest['macd']):.3f}"
        if 'bb_upper' in df.columns:
            indicators['BB Upper'] = f"${float(latest['bb_upper']):.2f}"
        if 'bb_lower' in df.columns:
            indicators['BB Lower'] = f"${float(latest['bb_lower']):.2f}"
        if 'sma_20' in df.columns:
            indicators['SMA 20'] = f"${float(latest['sma_20']):.2f}"
        if 'sma_50' in df.columns:
            indicators['SMA 50'] = f"${float(latest['sma_50']):.2f}"
        if 'volatility_21' in df.columns:
            indicators['Volatility'] = f"{float(latest['volatility_21']):.1%}"

        self._update_panel_card(self.indicators_card, indicators)

        # ── AI Prediction card ─────────────────────────────────
        self._load_prediction(symbol)

    def _load_prediction(self, symbol: str):
        """Loads and displays the AI prediction for a symbol."""
        try:
            from services.prediction_service import PredictionService
            pred_svc = PredictionService()
            pred = pred_svc.get_prediction(symbol)

            if pred:
                icon = (
                    "📈" if pred['direction'] == 'UP' else
                    "📉" if pred['direction'] == 'DOWN' else "➖"
                )
                self._update_panel_card(self.prediction_card, {
                    'Model':      pred['model_used'].replace('_', ' ').title(),
                    'Direction':  f"{icon} {pred['direction']}",
                    'Predicted':  f"${pred['predicted_price']:.2f}",
                    'Change':     f"{pred['predicted_return_pct']:+.2f}%",
                    'Confidence': f"{pred['confidence']*100:.0f}%",
                })
            else:
                self._update_panel_card(self.prediction_card, {
                    'Status': 'No model — run train_models.py'
                })
        except Exception as e:
            logger.warning(f"Prediction load failed: {e}")
            self._update_panel_card(self.prediction_card, {
                'Status': 'Prediction unavailable'
            })

    def _on_error(self, error_msg: str):
        self.status_label.setText(f"Error: {error_msg}")
        logger.error(f"Chart load error: {error_msg}")

    def show_stock(self, symbol: str):
        """Public method — called from other windows."""
        idx = self.stock_selector.findText(symbol)
        if idx >= 0:
            self.stock_selector.setCurrentIndex(idx)
        else:
            self.load_stock(symbol)