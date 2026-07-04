"""
gui/dialogs/add_transaction_dialog.py
=======================================
Dialog for recording a buy or sell transaction.
Uses QFormLayout for clean label-field alignment
with no overlapping.
"""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QDoubleSpinBox,
    QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

DEFAULT_PORTFOLIO_ID = 1


class AddTransactionDialog(QDialog):
    """Modal dialog for recording a buy or sell transaction."""

    def __init__(self, portfolio_controller=None, parent=None):
        super().__init__(parent)
        self.portfolio_ctrl = portfolio_controller
        self.setWindowTitle("Add Transaction")
        self.setFixedSize(480, 520)
        self.setModal(True)
        self.setStyleSheet("QDialog { background-color: #0d1117; }")
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Title
        title = QLabel("Record Transaction")
        title.setStyleSheet(
            "color: #e6edf3; font-size: 20px; font-weight: bold;"
        )
        root.addWidget(title)

        sub = QLabel("Record a buy or sell trade against your portfolio.")
        sub.setStyleSheet("color: #8b949e; font-size: 12px;")
        root.addWidget(sub)

        # Form card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }
        """)

        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setVerticalSpacing(14)
        form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Symbol
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("e.g.  AAPL")
        self.symbol_input.setFixedHeight(40)
        self.symbol_input.setStyleSheet(self._input_style())
        self.symbol_input.textChanged.connect(
            lambda t: self.symbol_input.setText(t.upper())
        )
        form.addRow(self._lbl("Symbol:"), self.symbol_input)

        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["BUY", "SELL"])
        self.type_combo.setFixedHeight(40)
        self.type_combo.setStyleSheet(self._combo_style())
        self.type_combo.currentTextChanged.connect(self._update_total)
        form.addRow(self._lbl("Type:"), self.type_combo)

        # Shares
        self.qty_input = QDoubleSpinBox()
        self.qty_input.setRange(0.0001, 999_999)
        self.qty_input.setDecimals(4)
        self.qty_input.setValue(1.0)
        self.qty_input.setFixedHeight(40)
        self.qty_input.setStyleSheet(self._spinbox_style())
        self.qty_input.valueChanged.connect(self._update_total)
        form.addRow(self._lbl("Shares:"), self.qty_input)

        # Price
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.01, 999_999)
        self.price_input.setDecimals(2)
        self.price_input.setValue(100.00)
        self.price_input.setPrefix("$ ")
        self.price_input.setFixedHeight(40)
        self.price_input.setStyleSheet(self._spinbox_style())
        self.price_input.valueChanged.connect(self._update_total)
        form.addRow(self._lbl("Price ($):"), self.price_input)

        # Fees
        self.fees_input = QDoubleSpinBox()
        self.fees_input.setRange(0, 9_999)
        self.fees_input.setDecimals(2)
        self.fees_input.setValue(0.00)
        self.fees_input.setPrefix("$ ")
        self.fees_input.setFixedHeight(40)
        self.fees_input.setStyleSheet(self._spinbox_style())
        self.fees_input.valueChanged.connect(self._update_total)
        form.addRow(self._lbl("Fees ($):"), self.fees_input)

        # Notes
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional note...")
        self.notes_input.setFixedHeight(40)
        self.notes_input.setStyleSheet(self._input_style())
        form.addRow(self._lbl("Notes:"), self.notes_input)

        root.addWidget(card)

        # Total preview
        total_row = QHBoxLayout()
        total_title = QLabel("Total:")
        total_title.setStyleSheet("color: #8b949e; font-size: 14px;")
        self.total_label = QLabel("$100.00")
        self.total_label.setStyleSheet(
            "color: #3fb950; font-size: 20px; font-weight: bold;"
        )
        total_row.addWidget(total_title)
        total_row.addStretch()
        total_row.addWidget(self.total_label)
        root.addLayout(total_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(44)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Record Transaction")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton:pressed { background-color: #1a6129; }
        """)
        save_btn.clicked.connect(self._save)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

        self._update_total()

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #8b949e; font-size: 13px; "
            "background: transparent; border: none;"
        )
        lbl.setFixedWidth(80)
        return lbl

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #1f6feb; }
        """

    def _spinbox_style(self) -> str:
        return """
            QDoubleSpinBox {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 13px;
            }
            QDoubleSpinBox:focus { border-color: #1f6feb; }
            QDoubleSpinBox::up-button {
                background-color: #21262d;
                border-left: 1px solid #30363d;
                border-top-right-radius: 6px;
                width: 22px;
            }
            QDoubleSpinBox::down-button {
                background-color: #21262d;
                border-left: 1px solid #30363d;
                border-bottom-right-radius: 6px;
                width: 22px;
            }
            QDoubleSpinBox::up-button:hover,
            QDoubleSpinBox::down-button:hover {
                background-color: #30363d;
            }
        """

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 13px;
            }
            QComboBox:focus { border-color: #1f6feb; }
            QComboBox::drop-down {
                background-color: #21262d;
                border-left: 1px solid #30363d;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                width: 26px;
            }
            QComboBox QAbstractItemView {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                selection-background-color: #1f6feb;
                font-size: 13px;
            }
        """

    def _update_total(self):
        total  = (self.qty_input.value() * self.price_input.value()
                  + self.fees_input.value())
        t_type = self.type_combo.currentText()
        color  = "#3fb950" if t_type == "BUY" else "#f85149"
        self.total_label.setText(f"${total:,.2f}")
        self.total_label.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: bold;"
        )

    def _save(self):
        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            QMessageBox.warning(
                self, "Missing Symbol",
                "Please enter a stock symbol (e.g. AAPL)."
            )
            return
        if not self.portfolio_ctrl:
            QMessageBox.warning(
                self, "Error",
                "Portfolio controller unavailable. Please restart."
            )
            return
        result = self.portfolio_ctrl.add_transaction(
            portfolio_id     = DEFAULT_PORTFOLIO_ID,
            symbol           = symbol,
            transaction_type = self.type_combo.currentText(),
            quantity         = self.qty_input.value(),
            price            = self.price_input.value(),
            fees             = self.fees_input.value(),
            notes            = self.notes_input.text().strip() or None,
        )
        if result['success']:
            QMessageBox.information(
                self, "Success", f"✅  {result['message']}"
            )
            self.accept()
        else:
            QMessageBox.warning(
                self, "Failed", f"❌  {result['message']}"
            )