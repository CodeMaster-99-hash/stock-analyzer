"""
gui/widgets/chart_widget.py
============================
Embeds Matplotlib charts inside the PyQt6 GUI.

HOW MATPLOTLIB WORKS INSIDE PYQT6:
    Normally Matplotlib shows charts in its own window.
    To embed it in our GUI we use FigureCanvasQTAgg —
    a special Qt widget that renders a Matplotlib Figure.
    We treat it like any other QWidget.
"""

import logging
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')  # Must be set before importing pyplot
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

# Dark theme colors matching our QSS
DARK_BG     = '#0d1117'
CARD_BG     = '#161b22'
BORDER      = '#30363d'
TEXT        = '#e6edf3'
MUTED       = '#8b949e'
BLUE        = '#1f6feb'
GREEN       = '#3fb950'
RED         = '#f85149'
ORANGE      = '#e3b341'
PURPLE      = '#bc8cff'


class ChartWidget(QWidget):
    """
    Embeds a Matplotlib chart into the PyQt6 application.
    Supports line charts, candlestick-style charts, and indicators.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df     = None
        self.symbol = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Period selector buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.period_buttons = {}
        for label, days in [('1M', 30), ('3M', 90),
                             ('6M', 180), ('1Y', 365), ('2Y', 730)]:
            btn = QPushButton(label)
            btn.setFixedSize(50, 28)
            btn.clicked.connect(lambda _, d=days: self._on_period_changed(d))
            self.period_buttons[days] = btn
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Matplotlib canvas
        self.figure = Figure(
            figsize     = (10, 6),
            facecolor   = DARK_BG,
            tight_layout= True,
        )
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

        self._current_days = 365

    def _on_period_changed(self, days: int):
        """Called when a period button is clicked."""
        self._current_days = days
        if self.df is not None:
            self.plot_price_chart(self.df, self.symbol, days)

    def plot_price_chart(self, df: pd.DataFrame,
                          symbol: str, period_days: int = 365):
        """
        Plots price history with moving averages and volume.

        LAYOUT:
            Top panel    (70%): Price line + SMA20 + SMA50 + BB bands
            Bottom panel (30%): Volume bars
        """
        if df is None or df.empty:
            self._show_no_data_message()
            return

        self.df     = df
        self.symbol = symbol

        # Filter to requested period
        df_plot = df.tail(period_days).copy()

        self.figure.clear()

        # Create two subplots sharing the x-axis
        ax1 = self.figure.add_subplot(211)  # Price chart (top)
        ax2 = self.figure.add_subplot(212,  # Volume chart (bottom)
                                       sharex=ax1)

        self._style_axis(ax1)
        self._style_axis(ax2)

        dates = df_plot.index

        # ── Price line ─────────────────────────────────────
        ax1.plot(dates, df_plot['close'],
                 color=BLUE, linewidth=1.5,
                 label='Close', zorder=3)

        # ── Moving averages ─────────────────────────────────
        if 'sma_20' in df_plot.columns:
            ax1.plot(dates, df_plot['sma_20'],
                     color=ORANGE, linewidth=1.0,
                     linestyle='--', label='SMA 20', alpha=0.8)

        if 'sma_50' in df_plot.columns:
            ax1.plot(dates, df_plot['sma_50'],
                     color=PURPLE, linewidth=1.0,
                     linestyle='--', label='SMA 50', alpha=0.8)

        # ── Bollinger Bands ─────────────────────────────────
        if 'bb_upper' in df_plot.columns:
            ax1.fill_between(
                dates,
                df_plot['bb_upper'],
                df_plot['bb_lower'],
                alpha   = 0.08,
                color   = BLUE,
                label   = 'BB Bands'
            )
            ax1.plot(dates, df_plot['bb_upper'],
                     color=BLUE, linewidth=0.5, alpha=0.4)
            ax1.plot(dates, df_plot['bb_lower'],
                     color=BLUE, linewidth=0.5, alpha=0.4)

        ax1.set_title(
            f'{symbol} — Price Chart',
            color=TEXT, fontsize=14, pad=10
        )
        ax1.set_ylabel('Price (USD)', color=MUTED, fontsize=10)
        ax1.legend(
            loc='upper left', fontsize=9,
            facecolor=CARD_BG, edgecolor=BORDER,
            labelcolor=TEXT
        )

        # ── Volume bars ─────────────────────────────────────
        colors = [
            GREEN if df_plot['close'].iloc[i] >= df_plot['close'].iloc[i-1]
            else RED
            for i in range(len(df_plot))
        ]
        ax2.bar(dates, df_plot['volume'],
                color=colors, alpha=0.7, width=0.8)
        ax2.set_ylabel('Volume', color=MUTED, fontsize=10)

        # ── Date formatting ─────────────────────────────────
        ax2.xaxis.set_major_formatter(
            mdates.DateFormatter('%b %Y')
        )
        ax2.xaxis.set_major_locator(
            mdates.MonthLocator(interval=2)
        )
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right')

        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

    def plot_rsi_chart(self, df: pd.DataFrame, symbol: str):
        """Plots RSI indicator with overbought/oversold lines."""
        if df is None or df.empty or 'rsi_14' not in df.columns:
            self._show_no_data_message()
            return

        df_plot = df.tail(365).copy()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._style_axis(ax)

        dates = df_plot.index

        ax.plot(dates, df_plot['rsi_14'],
                color=PURPLE, linewidth=1.5, label='RSI 14')

        # Overbought/oversold reference lines
        ax.axhline(y=70, color=RED,   linewidth=1.0,
                   linestyle='--', alpha=0.7, label='Overbought (70)')
        ax.axhline(y=30, color=GREEN, linewidth=1.0,
                   linestyle='--', alpha=0.7, label='Oversold (30)')
        ax.axhline(y=50, color=MUTED, linewidth=0.5,
                   linestyle=':', alpha=0.5)

        # Shade overbought and oversold zones
        ax.fill_between(dates, 70, 100,
                        alpha=0.05, color=RED)
        ax.fill_between(dates, 0, 30,
                        alpha=0.05, color=GREEN)

        ax.set_ylim(0, 100)
        ax.set_title(f'{symbol} — RSI (14)',
                     color=TEXT, fontsize=14)
        ax.set_ylabel('RSI', color=MUTED, fontsize=10)
        ax.legend(facecolor=CARD_BG, edgecolor=BORDER,
                  labelcolor=TEXT, fontsize=9)

        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

    def plot_macd_chart(self, df: pd.DataFrame, symbol: str):
        """Plots MACD line, signal line, and histogram."""
        if df is None or df.empty or 'macd' not in df.columns:
            self._show_no_data_message()
            return

        df_plot = df.tail(365).copy()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._style_axis(ax)

        dates = df_plot.index

        ax.plot(dates, df_plot['macd'],
                color=BLUE, linewidth=1.5, label='MACD')
        ax.plot(dates, df_plot['macd_signal'],
                color=ORANGE, linewidth=1.0, label='Signal')

        # Histogram — green when MACD > signal, red otherwise
        hist = df_plot['macd_hist']
        ax.bar(dates, hist,
               color=[GREEN if v >= 0 else RED for v in hist],
               alpha=0.5, width=0.8, label='Histogram')

        ax.axhline(y=0, color=MUTED, linewidth=0.5, linestyle='-')

        ax.set_title(f'{symbol} — MACD',
                     color=TEXT, fontsize=14)
        ax.set_ylabel('MACD', color=MUTED, fontsize=10)
        ax.legend(facecolor=CARD_BG, edgecolor=BORDER,
                  labelcolor=TEXT, fontsize=9)

        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

    def _style_axis(self, ax):
        """Applies dark theme styling to a Matplotlib axis."""
        ax.set_facecolor(CARD_BG)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.spines['bottom'].set_color(BORDER)
        ax.spines['top'].set_color(BORDER)
        ax.spines['left'].set_color(BORDER)
        ax.spines['right'].set_color(BORDER)
        ax.yaxis.label.set_color(MUTED)
        ax.xaxis.label.set_color(MUTED)
        ax.grid(True, color=BORDER, linewidth=0.5,
                linestyle='--', alpha=0.5)

    def _show_no_data_message(self):
        """Shows a placeholder when no data is available."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(DARK_BG)
        ax.text(
            0.5, 0.5,
            'No data available\nFetch stock data first',
            transform            = ax.transAxes,
            ha                   = 'center',
            va                   = 'center',
            color                = MUTED,
            fontsize             = 14,
        )
        ax.axis('off')
        self.canvas.draw()
