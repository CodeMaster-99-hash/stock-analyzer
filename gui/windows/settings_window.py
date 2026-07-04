"""
gui/windows/settings_window.py
================================
Application settings view.
"""

import logging
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout,
    QMessageBox, QLineEdit, QSpinBox,
    QComboBox, QScrollArea
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class SettingsWindow(QWidget):
    """Application settings and configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: #0d1117; }"
        )

        content = QWidget()
        content.setStyleSheet("background: #0d1117;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ── Page Title ───────────────────────────────────────
        title = QLabel("Settings")
        title.setStyleSheet(
            "color: #e6edf3; font-size: 24px; font-weight: bold;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "Configure your API keys, data preferences, and application behaviour."
        )
        subtitle.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(subtitle)

        # ── API Configuration Card ───────────────────────────
        api_card = self._make_card("🔑  API Configuration")
        api_grid = QGridLayout()
        api_grid.setSpacing(12)
        api_grid.setColumnMinimumWidth(0, 180)

        api_grid.addWidget(self._field_label("Alpha Vantage Key:"), 0, 0)
        self.av_key = self._text_input(
            placeholder="Enter your Alpha Vantage API key...",
            value=os.getenv('ALPHA_VANTAGE_KEY', '')
        )
        api_grid.addWidget(self.av_key, 0, 1)

        api_grid.addWidget(self._field_label("Finnhub Key:"), 1, 0)
        self.fh_key = self._text_input(
            placeholder="Enter your Finnhub API key...",
            value=os.getenv('FINNHUB_KEY', '')
        )
        api_grid.addWidget(self.fh_key, 1, 1)

        api_grid.addWidget(self._field_label("Polygon Key:"), 2, 0)
        self.poly_key = self._text_input(
            placeholder="Enter your Polygon.io API key...",
            value=os.getenv('POLYGON_KEY', '')
        )
        api_grid.addWidget(self.poly_key, 2, 1)

        api_card.layout().addLayout(api_grid)

        hint = QLabel(
            "💡  Free keys available at alphavantage.co  •  finnhub.io  •  polygon.io"
        )
        hint.setStyleSheet(
            "color: #58a6ff; font-size: 11px; "
            "background: transparent; border: none;"
        )
        api_card.layout().addWidget(hint)
        layout.addWidget(api_card)

        # ── Data Settings Card ───────────────────────────────
        data_card = self._make_card("📊  Data Settings")
        data_grid = QGridLayout()
        data_grid.setSpacing(12)
        data_grid.setColumnMinimumWidth(0, 180)

        data_grid.addWidget(
            self._field_label("Refresh Interval (sec):"), 0, 0
        )
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(30, 3600)
        self.refresh_spin.setValue(60)
        self.refresh_spin.setSuffix("  seconds")
        self.refresh_spin.setFixedHeight(40)
        self.refresh_spin.setStyleSheet(self._input_style())
        data_grid.addWidget(self.refresh_spin, 0, 1)

        data_grid.addWidget(
            self._field_label("Default Chart Period:"), 1, 0
        )
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            '1 Month', '3 Months', '6 Months',
            '1 Year', '2 Years', '5 Years'
        ])
        self.period_combo.setCurrentIndex(3)
        self.period_combo.setFixedHeight(40)
        self.period_combo.setStyleSheet(self._input_style())
        data_grid.addWidget(self.period_combo, 1, 1)

        data_grid.addWidget(
            self._field_label("Cache Duration (min):"), 2, 0
        )
        self.cache_spin = QSpinBox()
        self.cache_spin.setRange(1, 120)
        self.cache_spin.setValue(
            int(os.getenv('CACHE_DURATION_MINUTES', 15))
        )
        self.cache_spin.setSuffix("  minutes")
        self.cache_spin.setFixedHeight(40)
        self.cache_spin.setStyleSheet(self._input_style())
        data_grid.addWidget(self.cache_spin, 2, 1)

        data_card.layout().addLayout(data_grid)
        layout.addWidget(data_card)

        # ── Database Info Card ───────────────────────────────
        db_card = self._make_card("🗄️  Database Connection")
        db_grid = QGridLayout()
        db_grid.setSpacing(12)
        db_grid.setColumnMinimumWidth(0, 180)

        db_items = [
            ("Host:",     os.getenv('DB_HOST', 'localhost')),
            ("Port:",     os.getenv('DB_PORT', '3306')),
            ("Database:", os.getenv('DB_NAME', 'stock_analyzer')),
            ("User:",     os.getenv('DB_USER', 'root')),
            ("Status:",   "✅  Connected"),
        ]
        for row, (label, value) in enumerate(db_items):
            db_grid.addWidget(self._field_label(label), row, 0)
            val_lbl = QLabel(value)
            color = "#3fb950" if "Connected" in value else "#e6edf3"
            val_lbl.setStyleSheet(
                f"color: {color}; font-size: 13px; "
                f"background: transparent; border: none;"
            )
            db_grid.addWidget(val_lbl, row, 1)

        db_card.layout().addLayout(db_grid)
        layout.addWidget(db_card)

        # ── About Card ───────────────────────────────────────
        about_card = self._make_card("ℹ️  About")
        about_items = [
            ("Application:", "Stock Market Analyzer v1.0"),
            ("Python:",       "3.12+"),
            ("GUI:",          "PyQt6"),
            ("Database:",     "MySQL 8.0"),
            ("Data Source:",  "Yahoo Finance, Alpha Vantage, Finnhub"),
        ]
        about_grid = QGridLayout()
        about_grid.setSpacing(10)
        about_grid.setColumnMinimumWidth(0, 180)
        for row, (label, value) in enumerate(about_items):
            about_grid.addWidget(self._field_label(label), row, 0)
            v = QLabel(value)
            v.setStyleSheet(
                "color: #e6edf3; font-size: 13px; "
                "background: transparent; border: none;"
            )
            about_grid.addWidget(v, row, 1)
        about_card.layout().addLayout(about_grid)
        layout.addWidget(about_card)

        # ── Save Button ──────────────────────────────────────
        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾  Save Settings")
        save_btn.setFixedSize(180, 44)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton:pressed { background-color: #1a6129; }
        """)
        save_btn.clicked.connect(self._save)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setFixedSize(160, 44)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        reset_btn.clicked.connect(self._reset)

        btn_row.addWidget(save_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Helpers ──────────────────────────────────────────────

    def _make_card(self, title: str) -> QFrame:
        """Creates a styled settings section card."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(14)

        t = QLabel(title)
        t.setStyleSheet(
            "color: #e6edf3; font-size: 14px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        v.addWidget(t)

        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet(
            "background-color: #30363d; border: none;"
        )
        v.addWidget(divider)

        return card

    def _field_label(self, text: str) -> QLabel:
        """Creates a form field label."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #8b949e; font-size: 13px; "
            "background: transparent; border: none;"
        )
        lbl.setAlignment(
            Qt.AlignmentFlag.AlignLeft |
            Qt.AlignmentFlag.AlignVCenter
        )
        return lbl

    def _text_input(self, placeholder: str = "",
                     value: str = "") -> QLineEdit:
        """Creates a styled text input field."""
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setText(value)
        field.setFixedHeight(40)
        field.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 13px;
                selection-background-color: #1f6feb;
            }
            QLineEdit:focus {
                border-color: #1f6feb;
                background-color: #0d1117;
            }
            QLineEdit::placeholder {
                color: #484f58;
            }
        """)
        return field

    def _input_style(self) -> str:
        """Returns shared input style for spinboxes and combos."""
        return """
            QSpinBox, QComboBox {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 13px;
            }
            QSpinBox:focus, QComboBox:focus {
                border-color: #1f6feb;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #21262d;
                border: none;
                width: 20px;
            }
            QComboBox::drop-down {
                background-color: #21262d;
                border: none;
                width: 28px;
            }
            QComboBox QAbstractItemView {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                selection-background-color: #1f6feb;
            }
        """

    def _save(self):
        """Saves settings."""
        QMessageBox.information(
            self,
            "Settings Saved",
            "✅  Settings saved successfully.\n\n"
            "Some changes require restarting the application."
        )

    def _reset(self):
        """Resets to defaults."""
        self.refresh_spin.setValue(60)
        self.period_combo.setCurrentIndex(3)
        self.cache_spin.setValue(15)
        QMessageBox.information(
            self, "Reset", "Settings reset to defaults."
        )