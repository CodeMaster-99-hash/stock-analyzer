import logging

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QFrame,
    QGridLayout,
    QComboBox,
    QScrollArea,
)

from gui.widgets.chart_widget import ChartWidget


logger = logging.getLogger(__name__)


class DataLoadThread(QThread):

    data_ready = pyqtSignal(object, str)
    error_signal = pyqtSignal(str)

    def __init__(self, symbol, analytics_service):
        super().__init__()
        self.symbol = symbol
        self.analytics = analytics_service

    def run(self):

        try:
            df = self.analytics.get_enriched_data(
                self.symbol,
                365
            )

            self.data_ready.emit(
                df,
                self.symbol
            )

        except Exception as error:
            self.error_signal.emit(str(error))


class TrainModelThread(QThread):

    train_done = pyqtSignal(dict)

    def __init__(self, symbol, prediction_service):
        super().__init__()

        self.symbol = symbol
        self.prediction_service = prediction_service

    def run(self):

        try:

            logger.info(
                "Training model for %s",
                self.symbol
            )

            self.prediction_service.train_models_for_stock(
                self.symbol
            )

            prediction = (
                self.prediction_service
                .get_prediction(self.symbol)
            )

            self.train_done.emit(
                prediction or {}
            )

        except Exception as error:

            logger.warning(
                "Model training failed for %s: %s",
                self.symbol,
                error
            )

            self.train_done.emit({})


class ChartWindow(QWidget):

    def __init__(
        self,
        analytics_service=None,
        stock_controller=None,
        parent=None
    ):

        super().__init__(parent)

        self.analytics = analytics_service
        self.stock_ctrl = stock_controller

        self.current_df = None
        self.current_sym = ""

        self.load_thread = None
        self.train_thread = None

        self.setup_ui()

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            28,
            24,
            28,
            24
        )

        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        stock_label = QLabel("Stock:")

        stock_label.setStyleSheet("""
            color: #8b949e;
            font-size: 13px;
        """)

        self.stock_selector = QComboBox()

        self.stock_selector.setFixedWidth(180)
        self.stock_selector.setFixedHeight(36)

        self.stock_selector.addItems([
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "TSLA",
            "NVDA",
            "META",
            "JPM",
            "JNJ",
            "V"
        ])

        self.stock_selector.setStyleSheet("""
            QComboBox {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 13px;
                font-weight: bold;
            }

            QComboBox:focus {
                border-color: #1f6feb;
            }

            QComboBox::drop-down {
                background-color: #21262d;
                border-left: 1px solid #30363d;
                width: 26px;
            }

            QComboBox QAbstractItemView {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                selection-background-color: #1f6feb;
            }
        """)

        self.stock_selector.currentTextChanged.connect(
            self.load_stock
        )

        self.status_label = QLabel(
            "Select a stock or search from the dashboard"
        )

        self.status_label.setStyleSheet("""
            color: #8b949e;
            font-size: 12px;
        """)

        header.addWidget(stock_label)
        header.addWidget(self.stock_selector)
        header.addSpacing(12)
        header.addWidget(self.status_label)
        header.addStretch()

        layout.addLayout(header)

        # Main content
        content = QHBoxLayout()
        content.setSpacing(16)

        # Charts
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
                padding: 9px 22px;
                margin-right: 2px;
                font-size: 13px;
            }

            QTabBar::tab:selected {
                background-color: #161b22;
                color: #e6edf3;
                border-bottom: 2px solid #1f6feb;
                font-weight: bold;
            }

            QTabBar::tab:hover {
                color: #e6edf3;
            }
        """)

        self.price_chart = ChartWidget()
        self.rsi_chart = ChartWidget()
        self.macd_chart = ChartWidget()

        self.chart_tabs.addTab(
            self.price_chart,
            "Price"
        )

        self.chart_tabs.addTab(
            self.rsi_chart,
            "RSI"
        )

        self.chart_tabs.addTab(
            self.macd_chart,
            "MACD"
        )

        content.addWidget(
            self.chart_tabs,
            stretch=7
        )

        # Right panel
        self.indicator_panel = (
            self.build_indicator_panel()
        )

        content.addWidget(
            self.indicator_panel,
            stretch=3
        )

        layout.addLayout(content)

    # ---------------------------------------------------------
    # Indicator Panel
    # ---------------------------------------------------------

    def build_indicator_panel(self):

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)
        scroll.setMaximumWidth(300)

        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        container = QWidget()

        container.setStyleSheet(
            "background: transparent;"
        )

        layout = QVBoxLayout(container)

        layout.setSpacing(12)
        layout.setContentsMargins(
            0,
            0,
            8,
            0
        )

        self.info_card = self.make_panel_card(
            "Stock Info"
        )

        self.price_card = self.make_panel_card(
            "Price Summary"
        )

        self.indicators_card = self.make_panel_card(
            "Indicators"
        )

        self.prediction_card = self.make_panel_card(
            "AI Prediction"
        )

        layout.addWidget(self.info_card)
        layout.addWidget(self.price_card)
        layout.addWidget(self.indicators_card)
        layout.addWidget(self.prediction_card)

        layout.addStretch()

        scroll.setWidget(container)

        return scroll

    def make_panel_card(self, title):

        card = QFrame()

        card.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(card)

        layout.setSpacing(8)
        layout.setContentsMargins(
            16,
            14,
            16,
            14
        )

        title_label = QLabel(title)

        title_label.setStyleSheet("""
            color: #8b949e;
            font-size: 11px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)

        layout.addWidget(title_label)

        grid = QGridLayout()

        grid.setSpacing(6)

        layout.addLayout(grid)

        card.grid = grid
        card.rows = []

        return card

    def update_panel_card(self, card, data):

        for widgets in card.rows:

            for widget in widgets:
                widget.deleteLater()

        card.rows.clear()

        row = 0

        for key, value in data.items():

            if value is None:
                continue

            key_label = QLabel(str(key))

            key_label.setStyleSheet("""
                color: #8b949e;
                font-size: 11px;
                background: transparent;
                border: none;
            """)

            value_label = QLabel(str(value))

            value_label.setWordWrap(True)

            value_label.setStyleSheet("""
                color: #e6edf3;
                font-size: 11px;
                font-weight: bold;
                background: transparent;
                border: none;
            """)

            value_label.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )

            card.grid.addWidget(
                key_label,
                row,
                0
            )

            card.grid.addWidget(
                value_label,
                row,
                1
            )

            card.rows.append(
                [key_label, value_label]
            )

            row += 1

    # ---------------------------------------------------------
    # Stock Loading
    # ---------------------------------------------------------

    def load_stock(self, symbol):

        if not symbol or self.analytics is None:
            return

        symbol = symbol.upper().strip()

        self.current_sym = symbol

        self.status_label.setText(
            f"Loading {symbol}..."
        )

        if (
            self.load_thread
            and self.load_thread.isRunning()
        ):

            self.load_thread.quit()
            self.load_thread.wait()

        self.load_thread = DataLoadThread(
            symbol,
            self.analytics
        )

        self.load_thread.data_ready.connect(
            self.on_data_ready
        )

        self.load_thread.error_signal.connect(
            self.on_error
        )

        self.load_thread.start()

    def show_stock(self, symbol):

        if not symbol:
            return

        symbol = symbol.upper().strip()

        self.stock_selector.blockSignals(True)

        index = self.stock_selector.findText(
            symbol
        )

        if index == -1:

            self.stock_selector.addItem(
                symbol
            )

            index = (
                self.stock_selector.count() - 1
            )

        self.stock_selector.setCurrentIndex(
            index
        )

        self.stock_selector.blockSignals(False)

        self.load_stock(symbol)

    # ---------------------------------------------------------
    # Data Ready
    # ---------------------------------------------------------

    def on_data_ready(self, df, symbol):

        if df is None:
            self.on_error(
                "No data returned"
            )
            return

        self.current_df = df
        self.current_sym = symbol

        self.status_label.setText(
            f"{symbol} - {len(df)} trading days loaded"
        )

        self.price_chart.plot_price_chart(
            df,
            symbol
        )

        self.rsi_chart.plot_rsi_chart(
            df,
            symbol
        )

        self.macd_chart.plot_macd_chart(
            df,
            symbol
        )

        self.update_stock_info(
            symbol
        )

        if df.empty:

            self.update_panel_card(
                self.price_card,
                {"Status": "No price data"}
            )

            self.update_panel_card(
                self.indicators_card,
                {"Status": "No indicator data"}
            )

            self.update_panel_card(
                self.prediction_card,
                {"Status": "No data available"}
            )

            return

        self.update_price_summary(df)

        self.update_indicators(df)

        self.load_prediction(symbol)

    # ---------------------------------------------------------
    # Stock Information
    # ---------------------------------------------------------

    def update_stock_info(self, symbol):

        if self.stock_ctrl is None:

            self.update_panel_card(
                self.info_card,
                {"Status": "Controller unavailable"}
            )

            return

        try:

            result = (
                self.stock_ctrl
                .get_stock_detail(symbol)
            )

            if (
                result.get("success")
                and result.get("data")
            ):

                data = result["data"]

                self.update_panel_card(
                    self.info_card,
                    {
                        "Name":
                            data.get("name") or symbol,

                        "Sector":
                            data.get("sector") or "—",

                        "Industry":
                            data.get("industry") or "—",

                        "Exchange":
                            data.get("exchange") or "—",

                        "Currency":
                            data.get("currency") or "USD"
                    }
                )

            else:

                self.update_panel_card(
                    self.info_card,
                    {
                        "Symbol": symbol,
                        "Status":
                            "Details unavailable"
                    }
                )

        except Exception as error:

            logger.warning(
                "Stock detail error: %s",
                error
            )

            self.update_panel_card(
                self.info_card,
                {
                    "Symbol": symbol,
                    "Status": "Details unavailable"
                }
            )

    # ---------------------------------------------------------
    # Price Summary
    # ---------------------------------------------------------

    def update_price_summary(self, df):

        latest = df.iloc[-1]

        current = float(
            latest["close"]
        )

        previous = (
            float(df["close"].iloc[-2])
            if len(df) > 1
            else None
        )

        average_volume = (
            float(df["volume"].mean())
            if "volume" in df.columns
            else 0
        )

        data = {
            "Current":
                f"${current:,.2f}",

            "Prev Close":
                f"${previous:,.2f}"
                if previous is not None
                else "—",

            "52W High":
                f"${float(df['close'].max()):,.2f}",

            "52W Low":
                f"${float(df['close'].min()):,.2f}",

            "Avg Volume":
                f"{int(average_volume):,}"
        }

        self.update_panel_card(
            self.price_card,
            data
        )

    # ---------------------------------------------------------
    # Indicators
    # ---------------------------------------------------------

    def update_indicators(self, df):

        latest = df.iloc[-1]

        indicators = {}

        if "rsi_14" in df.columns:

            value = latest["rsi_14"]

            if pd_not_null(value):

                rsi = float(value)

                if rsi > 70:
                    status = " Overbought"

                elif rsi < 30:
                    status = " Oversold"

                else:
                    status = ""

                indicators["RSI (14)"] = (
                    f"{rsi:.1f}{status}"
                )

        if "macd" in df.columns:

            value = latest["macd"]

            if pd_not_null(value):

                indicators["MACD"] = (
                    f"{float(value):.4f}"
                )

        if "bb_upper" in df.columns:

            value = latest["bb_upper"]

            if pd_not_null(value):

                indicators["BB Upper"] = (
                    f"${float(value):,.2f}"
                )

        if "bb_lower" in df.columns:

            value = latest["bb_lower"]

            if pd_not_null(value):

                indicators["BB Lower"] = (
                    f"${float(value):,.2f}"
                )

        if "sma_20" in df.columns:

            value = latest["sma_20"]

            if pd_not_null(value):

                indicators["SMA 20"] = (
                    f"${float(value):,.2f}"
                )

        if "sma_50" in df.columns:

            value = latest["sma_50"]

            if pd_not_null(value):

                indicators["SMA 50"] = (
                    f"${float(value):,.2f}"
                )

        if "volatility_21" in df.columns:

            value = latest["volatility_21"]

            if pd_not_null(value):

                indicators["Volatility"] = (
                    f"{float(value):.1%}"
                )

        if indicators:

            self.update_panel_card(
                self.indicators_card,
                indicators
            )

        else:

            self.update_panel_card(
                self.indicators_card,
                {
                    "Status":
                        "No indicator data available"
                }
            )

    # ---------------------------------------------------------
    # AI Prediction
    # ---------------------------------------------------------

    def load_prediction(self, symbol):

        try:

            from services.prediction_service import (
                PredictionService
            )

            prediction_service = (
                PredictionService()
            )

            prediction = (
                prediction_service
                .get_prediction(symbol)
            )

            if (
                prediction
                and prediction.get(
                    "predicted_price"
                )
            ):

                self.show_prediction(
                    prediction
                )

            else:

                self.update_panel_card(
                    self.prediction_card,
                    {
                        "Status":
                            "Training model...",
                        "Note":
                            "First training may take time"
                    }
                )

                self.auto_train_model(
                    symbol,
                    prediction_service
                )

        except Exception as error:

            logger.warning(
                "Prediction error: %s",
                error
            )

            self.update_panel_card(
                self.prediction_card,
                {
                    "Status":
                        "Prediction unavailable"
                }
            )

    def auto_train_model(
        self,
        symbol,
        prediction_service
    ):

        if (
            self.train_thread
            and self.train_thread.isRunning()
        ):

            self.train_thread.quit()
            self.train_thread.wait()

        self.train_thread = TrainModelThread(
            symbol,
            prediction_service
        )

        self.train_thread.train_done.connect(
            self.on_train_done
        )

        self.train_thread.start()

    def on_train_done(self, prediction):

        if (
            prediction
            and prediction.get("predicted_price")
        ):

            self.show_prediction(
                prediction
            )

        else:

            self.update_panel_card(
                self.prediction_card,
                {
                    "Status":
                        "Prediction unavailable",
                    "Note":
                        "More historical data may be required"
                }
            )

    def show_prediction(self, prediction):

        direction = prediction.get(
            "direction",
            "FLAT"
        )

        if direction == "UP":
            icon = "↑"

        elif direction == "DOWN":
            icon = "↓"

        else:
            icon = "→"

        model_name = str(
            prediction.get(
                "model_used",
                "—"
            )
        ).replace(
            "_",
            " "
        ).title()

        predicted_price = float(
            prediction.get(
                "predicted_price",
                0
            )
        )

        return_pct = float(
            prediction.get(
                "predicted_return_pct",
                0
            )
        )

        confidence = float(
            prediction.get(
                "confidence",
                0
            )
        )

        horizon = prediction.get(
            "horizon_days",
            1
        )

        sign = "+" if return_pct >= 0 else ""

        self.update_panel_card(
            self.prediction_card,
            {
                "Model":
                    model_name,

                "Direction":
                    f"{icon} {direction}",

                "Predicted":
                    f"${predicted_price:,.2f}",

                "Change":
                    f"{sign}{return_pct:.2f}%",

                "Confidence":
                    f"{confidence * 100:.0f}%",

                "Horizon":
                    f"{horizon} day(s)"
            }
        )

    # ---------------------------------------------------------
    # Error
    # ---------------------------------------------------------

    def on_error(self, error_message):

        self.status_label.setText(
            f"Error loading data: {error_message}"
        )

        logger.error(
            "Chart load error: %s",
            error_message
        )

        self.update_panel_card(
            self.info_card,
            {
                "Error":
                    error_message[:80]
            }
        )


def pd_not_null(value):

    if value is None:
        return False

    try:
        return not bool(
            __import__("pandas").isna(value)
        )

    except Exception:
        return True
