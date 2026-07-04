"""
gui/widgets/sidebar_widget.py
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QLabel, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt


class SidebarWidget(QWidget):

    navigation_requested = pyqtSignal(str)

    NAV_ITEMS = [
        ("Dashboard",  "dashboard"),
        ("Watchlist",  "watchlist"),
        ("Portfolio",  "portfolio"),
        ("Charts",     "charts"),
        ("Settings",   "settings"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)
        self._buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(6)

        title = QLabel("📈 StockAnalyzer")
        title.setFixedHeight(36)
        title.setStyleSheet("""
            color: #58a6ff;
            font-size: 16px;
            font-weight: bold;
            padding-left: 8px;
        """)
        layout.addWidget(title)

        version = QLabel("Professional Edition v1.0")
        version.setFixedHeight(24)
        version.setStyleSheet("""
            color: #8b949e;
            font-size: 10px;
            padding-left: 8px;
            margin-bottom: 12px;
        """)
        layout.addWidget(version)

        # Divider
        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #30363d; margin: 4px 0px;")
        layout.addWidget(divider)

        layout.addSpacing(8)

        for label, key in self.NAV_ITEMS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #8b949e;
                    border: none;
                    border-radius: 8px;
                    padding-left: 16px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #21262d;
                    color: #e6edf3;
                }
                QPushButton:checked {
                    background-color: #1f6feb;
                    color: #ffffff;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(
                lambda checked, k=key: self._on_nav_clicked(k)
            )
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addSpacerItem(QSpacerItem(
            20, 40,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding
        ))

        # Bottom info
        bottom = QLabel("Market data by Yahoo Finance")
        bottom.setStyleSheet("""
            color: #484f58;
            font-size: 10px;
            padding-left: 8px;
        """)
        bottom.setWordWrap(True)
        layout.addWidget(bottom)

        self.set_active_page("dashboard")

    def _on_nav_clicked(self, page_key: str):
        self.set_active_page(page_key)
        self.navigation_requested.emit(page_key)

    def set_active_page(self, page_key: str):
        for key, btn in self._buttons.items():
            btn.setChecked(key == page_key)