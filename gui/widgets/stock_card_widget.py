"""
gui/widgets/stock_card_widget.py
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt


class StockCardWidget(QFrame):

    clicked = pyqtSignal(str)

    def __init__(self, symbol: str, name: str,
                 price: float = 0.0,
                 change: float = 0.0,
                 change_pct: float = 0.0,
                 parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.setObjectName("StockCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(88)
        self.setStyleSheet("""
            QFrame#StockCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }
            QFrame#StockCard:hover {
                border: 1px solid #1f6feb;
                background-color: #1c2230;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Row 1 — Symbol | Price
        row1 = QHBoxLayout()
        row1.setSpacing(0)

        self.sym_lbl = QLabel(symbol)
        self.sym_lbl.setStyleSheet(
            "color: #e6edf3; font-size: 15px; font-weight: bold; "
            "background: transparent; border: none;"
        )

        self.price_lbl = QLabel(
            f"${price:,.2f}" if price else "—"
        )
        self.price_lbl.setStyleSheet(
            "color: #e6edf3; font-size: 15px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        self.price_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        row1.addWidget(self.sym_lbl)
        row1.addStretch()
        row1.addWidget(self.price_lbl)

        # Row 2 — Name | Change
        row2 = QHBoxLayout()
        row2.setSpacing(0)

        self.name_lbl = QLabel(name[:30])
        self.name_lbl.setStyleSheet(
            "color: #8b949e; font-size: 11px; "
            "background: transparent; border: none;"
        )

        self.change_lbl = QLabel()
        self.change_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._set_change(change, change_pct)

        row2.addWidget(self.name_lbl)
        row2.addStretch()
        row2.addWidget(self.change_lbl)

        layout.addLayout(row1)
        layout.addLayout(row2)

    def _set_change(self, change: float, change_pct: float):
        if change > 0:
            color, arrow = "#3fb950", "▲"
        elif change < 0:
            color, arrow = "#f85149", "▼"
        else:
            color, arrow = "#8b949e", "●"

        self.change_lbl.setText(
            f"{arrow} {abs(change):.2f}  ({abs(change_pct):.2f}%)"
        )
        self.change_lbl.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold; "
            f"background: transparent; border: none;"
        )

    def update_price(self, price: float,
                     change: float, change_pct: float):
        self.price_lbl.setText(f"${price:,.2f}")
        self._set_change(change, change_pct)

    def mousePressEvent(self, event):
        self.clicked.emit(self.symbol)
        super().mousePressEvent(event)