import logging

import pandas as pd
import matplotlib

matplotlib.use("QtAgg")

import matplotlib.dates as mdates
import matplotlib.ticker as mticker

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton


logger = logging.getLogger(__name__)


# Theme
DARK_BG = "#0d1117"
CARD_BG = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"

BLUE = "#1f6feb"
GREEN = "#3fb950"
RED = "#f85149"
ORANGE = "#e3b341"
PURPLE = "#bc8cff"


class ChartWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.df = None
        self.symbol = ""
        self.current_days = 365

        self.setup_ui()

    def setup_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)

        self.period_buttons = {}

        periods = {
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365,
            "2Y": 730
        }

        for label, days in periods.items():

            button = QPushButton(label)
            button.setFixedSize(52, 28)

            button.setStyleSheet("""
                QPushButton {
                    background-color: #21262d;
                    color: #8b949e;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }

                QPushButton:hover {
                    background-color: #30363d;
                    color: #e6edf3;
                }

                QPushButton:pressed {
                    background-color: #1f6feb;
                    color: white;
                    border-color: #1f6feb;
                }
            """)

            button.clicked.connect(
                lambda checked=False, d=days:
                self.on_period_changed(d)
            )

            self.period_buttons[days] = button
            button_layout.addWidget(button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        self.figure = Figure(
            figsize=(10, 6),
            facecolor=DARK_BG
        )

        self.canvas = FigureCanvasQTAgg(self.figure)

        layout.addWidget(self.canvas)

    # ---------------------------------------------------------
    # Period
    # ---------------------------------------------------------

    def on_period_changed(self, days):

        self.current_days = days

        if self.df is not None:
            self.plot_price_chart(
                self.df,
                self.symbol,
                days
            )

    # ---------------------------------------------------------
    # Price Chart
    # ---------------------------------------------------------

    def plot_price_chart(
        self,
        df: pd.DataFrame,
        symbol: str,
        period_days: int = 365
    ):

        if df is None or df.empty:
            self.show_no_data()
            return

        self.df = df
        self.symbol = symbol
        self.current_days = period_days

        df_plot = df.tail(period_days).copy()

        self.figure.clear()
        self.figure.patch.set_facecolor(DARK_BG)

        grid = self.figure.add_gridspec(
            2,
            1,
            height_ratios=[7, 3],
            hspace=0.08
        )

        price_ax = self.figure.add_subplot(grid[0])
        volume_ax = self.figure.add_subplot(
            grid[1],
            sharex=price_ax
        )

        self.style_axis(price_ax)
        self.style_axis(volume_ax)

        dates = df_plot.index

        # Close price
        if "close" in df_plot.columns:

            price_ax.plot(
                dates,
                df_plot["close"],
                color=BLUE,
                linewidth=2,
                label="Close Price"
            )

        # SMA 20
        if "sma_20" in df_plot.columns:

            sma20 = df_plot["sma_20"].dropna()

            if not sma20.empty:

                price_ax.plot(
                    sma20.index,
                    sma20,
                    color=ORANGE,
                    linewidth=1.3,
                    linestyle="--",
                    label="SMA 20"
                )

        # SMA 50
        if "sma_50" in df_plot.columns:

            sma50 = df_plot["sma_50"].dropna()

            if not sma50.empty:

                price_ax.plot(
                    sma50.index,
                    sma50,
                    color=PURPLE,
                    linewidth=1.3,
                    linestyle="--",
                    label="SMA 50"
                )

        # Bollinger Bands
        if (
            "bb_upper" in df_plot.columns
            and "bb_lower" in df_plot.columns
        ):

            upper = df_plot["bb_upper"].dropna()
            lower = df_plot["bb_lower"].dropna()

            common_index = upper.index.intersection(
                lower.index
            )

            if not common_index.empty:

                price_ax.fill_between(
                    common_index,
                    upper.loc[common_index],
                    lower.loc[common_index],
                    color=BLUE,
                    alpha=0.08
                )

                price_ax.plot(
                    common_index,
                    upper.loc[common_index],
                    color=BLUE,
                    linewidth=0.6,
                    alpha=0.5
                )

                price_ax.plot(
                    common_index,
                    lower.loc[common_index],
                    color=BLUE,
                    linewidth=0.6,
                    alpha=0.5
                )

        # Price formatting
        price_ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(
                lambda value, _: f"${value:,.2f}"
            )
        )

        if "close" in df_plot.columns:

            minimum = float(df_plot["close"].min())
            maximum = float(df_plot["close"].max())

            if maximum > minimum:

                padding = (maximum - minimum) * 0.05

                price_ax.set_ylim(
                    minimum - padding,
                    maximum + padding
                )

        price_ax.set_title(
            f"{symbol} - Price Chart",
            color=TEXT,
            fontsize=13,
            fontweight="bold"
        )

        price_ax.set_ylabel(
            "Price (USD)",
            color=MUTED
        )

        price_ax.legend(
            loc="upper left",
            fontsize=9,
            facecolor=CARD_BG,
            edgecolor=BORDER,
            labelcolor=TEXT
        )

        price_ax.tick_params(
            labelbottom=False
        )

        # Volume
        if "volume" in df_plot.columns:

            close_values = df_plot["close"].values

            volume_colors = []

            for index in range(len(df_plot)):

                if index == 0:
                    volume_colors.append(GREEN)

                elif close_values[index] >= close_values[index - 1]:
                    volume_colors.append(GREEN)

                else:
                    volume_colors.append(RED)

            volume_ax.bar(
                dates,
                df_plot["volume"],
                color=volume_colors,
                alpha=0.75,
                width=0.8
            )

        volume_ax.set_ylabel(
            "Volume",
            color=MUTED
        )

        volume_ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(self.format_volume)
        )

        self.format_dates(
            volume_ax,
            len(df_plot)
        )

        self.figure.tight_layout(pad=2)

        self.canvas.draw()

    # ---------------------------------------------------------
    # RSI
    # ---------------------------------------------------------

    def plot_rsi_chart(
        self,
        df: pd.DataFrame,
        symbol: str
    ):

        if (
            df is None
            or df.empty
            or "rsi_14" not in df.columns
        ):
            self.show_no_data()
            return

        df_plot = df.tail(365).copy()

        self.figure.clear()
        self.figure.patch.set_facecolor(DARK_BG)

        ax = self.figure.add_subplot(111)

        self.style_axis(ax)

        rsi = df_plot["rsi_14"].dropna()

        ax.plot(
            rsi.index,
            rsi,
            color=PURPLE,
            linewidth=1.8,
            label="RSI (14)"
        )

        ax.axhline(
            70,
            color=RED,
            linewidth=1.2,
            linestyle="--",
            label="Overbought (70)"
        )

        ax.axhline(
            50,
            color=MUTED,
            linewidth=0.8,
            linestyle=":"
        )

        ax.axhline(
            30,
            color=GREEN,
            linewidth=1.2,
            linestyle="--",
            label="Oversold (30)"
        )

        ax.fill_between(
            df_plot.index,
            70,
            100,
            color=RED,
            alpha=0.06
        )

        ax.fill_between(
            df_plot.index,
            0,
            30,
            color=GREEN,
            alpha=0.06
        )

        ax.set_ylim(0, 100)

        ax.set_yticks(
            [0, 20, 30, 50, 70, 80, 100]
        )

        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(
                lambda value, _: f"{value:.0f}"
            )
        )

        self.format_dates(ax, len(df_plot))

        ax.set_title(
            f"{symbol} - RSI (14)",
            color=TEXT,
            fontsize=13,
            fontweight="bold"
        )

        ax.set_ylabel(
            "RSI Value",
            color=MUTED
        )

        ax.legend(
            facecolor=CARD_BG,
            edgecolor=BORDER,
            labelcolor=TEXT,
            fontsize=9
        )

        self.figure.tight_layout(pad=2)

        self.canvas.draw()

    # ---------------------------------------------------------
    # MACD
    # ---------------------------------------------------------

    def plot_macd_chart(
        self,
        df: pd.DataFrame,
        symbol: str
    ):

        if (
            df is None
            or df.empty
            or "macd" not in df.columns
        ):
            self.show_no_data()
            return

        df_plot = df.tail(365).copy()

        self.figure.clear()
        self.figure.patch.set_facecolor(DARK_BG)

        ax = self.figure.add_subplot(111)

        self.style_axis(ax)

        dates = df_plot.index

        ax.plot(
            dates,
            df_plot["macd"],
            color=BLUE,
            linewidth=1.8,
            label="MACD"
        )

        if "macd_signal" in df_plot.columns:

            ax.plot(
                dates,
                df_plot["macd_signal"],
                color=ORANGE,
                linewidth=1.2,
                label="Signal"
            )

        if "macd_hist" in df_plot.columns:

            histogram = df_plot["macd_hist"]

            histogram_colors = [
                GREEN if value >= 0 else RED
                for value in histogram
            ]

            ax.bar(
                dates,
                histogram,
                color=histogram_colors,
                alpha=0.55,
                width=0.8,
                label="Histogram"
            )

        ax.axhline(
            0,
            color=MUTED,
            linewidth=0.8,
            alpha=0.5
        )

        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(
                lambda value, _: f"{value:.3f}"
            )
        )

        self.format_dates(ax, len(df_plot))

        ax.set_title(
            f"{symbol} - MACD (12, 26, 9)",
            color=TEXT,
            fontsize=13,
            fontweight="bold"
        )

        ax.set_ylabel(
            "MACD Value",
            color=MUTED
        )

        ax.legend(
            facecolor=CARD_BG,
            edgecolor=BORDER,
            labelcolor=TEXT,
            fontsize=9
        )

        self.figure.tight_layout(pad=2)

        self.canvas.draw()

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def format_volume(value, _):

        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"

        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"

        if value >= 1_000:
            return f"{value / 1_000:.0f}K"

        return str(int(value))

    @staticmethod
    def format_dates(ax, number_of_days):

        if number_of_days <= 35:

            ax.xaxis.set_major_locator(
                mdates.WeekdayLocator(interval=1)
            )

        elif number_of_days <= 90:

            ax.xaxis.set_major_locator(
                mdates.MonthLocator()
            )

        else:

            ax.xaxis.set_major_locator(
                mdates.MonthLocator(interval=2)
            )

        ax.xaxis.set_major_formatter(
            mdates.DateFormatter("%b %Y")
        )

        for label in ax.get_xticklabels():

            label.set_rotation(30)
            label.set_horizontalalignment("right")
            label.set_fontsize(8)

    @staticmethod
    def style_axis(ax):

        ax.set_facecolor(CARD_BG)

        ax.tick_params(
            colors=MUTED,
            labelsize=9
        )

        for spine in ax.spines.values():
            spine.set_color(BORDER)

        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)

        ax.grid(
            True,
            color=BORDER,
            linewidth=0.5,
            linestyle="--",
            alpha=0.4
        )

    def show_no_data(self):

        self.figure.clear()
        self.figure.patch.set_facecolor(DARK_BG)

        ax = self.figure.add_subplot(111)

        ax.set_facecolor(DARK_BG)

        ax.text(
            0.5,
            0.5,
            "No data available\n"
            "Search for a stock to view its chart",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=MUTED,
            fontsize=13
        )

        ax.axis("off")

        self.canvas.draw()
