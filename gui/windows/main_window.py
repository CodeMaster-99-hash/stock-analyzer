"""
gui/windows/main_window.py
===========================
Main application window.
"""

import logging
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QStackedWidget, QStatusBar, QLabel,
    QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from gui.widgets.sidebar_widget import SidebarWidget
from gui.windows.dashboard_window import DashboardWindow
from gui.windows.chart_window import ChartWindow
from gui.windows.portfolio_window import PortfolioWindow
from gui.windows.watchlist_window import WatchlistWindow
from gui.windows.settings_window import SettingsWindow

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._setup_status_bar()
        self._setup_services()
        self._setup_window()
        self._setup_menu_bar()
        self._setup_ui()
        self._connect_signals()
        self._setup_refresh_timer()
        logger.info("Main window initialised.")

    def _setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #161b22;
                color: #8b949e;
                border-top: 1px solid #30363d;
                font-size: 12px;
                padding: 0px 8px;
            }
        """)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        self.db_status = QLabel("● DB Connected")
        self.db_status.setStyleSheet(
            "color: #3fb950; padding-right: 16px;"
        )
        self.status_bar.addPermanentWidget(self.db_status)

    def _setup_services(self):
        from controllers.stock_controller     import StockController
        from controllers.portfolio_controller import PortfolioController
        from controllers.alert_controller     import AlertController
        from services.analytics_service       import AnalyticsService
        from services.data_fetcher_service    import DataFetcherService

        self.stock_ctrl     = StockController()
        self.portfolio_ctrl = PortfolioController()
        self.alert_ctrl     = AlertController()
        self.analytics      = AnalyticsService()
        self.data_fetcher   = DataFetcherService()
        logger.info("All services ready.")

    def _setup_window(self):
        self.setWindowTitle("Stock Market Analyzer")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        screen = self.screen().availableGeometry()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _setup_menu_bar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #161b22;
                color: #e6edf3;
                border-bottom: 1px solid #30363d;
                padding: 4px 0px;
                font-size: 13px;
            }
            QMenuBar::item:selected { background-color: #21262d; }
            QMenu {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
            }
            QMenu::item:selected { background-color: #1f6feb; }
        """)

        file_menu = menubar.addMenu("File")

        refresh_action = QAction("Refresh Data", self)
        refresh_action.setShortcut("Ctrl+R")
        refresh_action.triggered.connect(self._refresh_all)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("View")
        for label, page in [
            ("Dashboard",  "dashboard"),
            ("Watchlist",  "watchlist"),
            ("Portfolio",  "portfolio"),
            ("Charts",     "charts"),
            ("Settings",   "settings"),
        ]:
            action = QAction(label, self)
            action.triggered.connect(
                lambda _, p=page: self._navigate_to(p)
            )
            view_menu.addAction(action)

        help_menu = menubar.addMenu("Help")
        about = QAction("About", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #0d1117;")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = SidebarWidget()
        root.addWidget(self.sidebar)

        # Vertical divider line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet("background-color: #30363d;")
        root.addWidget(line)

        # Page stack
        self.page_stack = QStackedWidget()
        self.page_stack.setStyleSheet("background-color: #0d1117;")
        root.addWidget(self.page_stack)

        self.pages = {}
        self._add_page("dashboard", DashboardWindow(
            stock_controller=self.stock_ctrl
        ))
        self._add_page("watchlist", WatchlistWindow(
            stock_controller=self.stock_ctrl,
            data_fetcher    =self.data_fetcher,
        ))
        self._add_page("portfolio", PortfolioWindow(
            portfolio_controller=self.portfolio_ctrl,
            data_fetcher        =self.data_fetcher,
        ))
        self._add_page("charts", ChartWindow(
            analytics_service=self.analytics,
            stock_controller =self.stock_ctrl,
        ))
        self._add_page("settings", SettingsWindow())

        self._navigate_to("dashboard")

    def _add_page(self, key: str, widget: QWidget):
        self.pages[key] = widget
        self.page_stack.addWidget(widget)

    def _connect_signals(self):
        self.pages['dashboard'].stock_selected.connect(
            self._on_stock_selected
        )
        self.pages['watchlist'].stock_selected.connect(
            self._on_stock_selected
        )
        self.sidebar.navigation_requested.connect(self._navigate_to)

    def _setup_refresh_timer(self):
        interval = int(os.getenv('CACHE_DURATION_MINUTES', 15)) * 60 * 1000
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_all)
        self.refresh_timer.start(interval)

    def _navigate_to(self, page_key: str):
        if page_key in self.pages:
            self.page_stack.setCurrentWidget(self.pages[page_key])
            self.sidebar.set_active_page(page_key)
            self.status_label.setText(f"Viewing: {page_key.title()}")

    def _on_stock_selected(self, symbol: str):
        self._navigate_to("charts")
        self.pages['charts'].show_stock(symbol)
        self.status_label.setText(f"Viewing: {symbol}")

    def _refresh_all(self):
        self.status_label.setText("Refreshing...")
        try:
            if hasattr(self.pages.get('watchlist'), 'refresh'):
                self.pages['watchlist'].refresh()
            if hasattr(self.pages.get('portfolio'), 'refresh'):
                self.pages['portfolio'].refresh()
        except Exception as e:
            logger.error(f"Refresh error: {e}")
        self.status_label.setText("Ready")

    def _show_about(self):
        QMessageBox.about(
            self,
            "About Stock Market Analyzer",
            "<h3>Stock Market Analyzer v1.0</h3>"
            "<p>Professional desktop stock analysis application.</p>"
            "<p>Built with Python 3.12, PyQt6, MySQL, Matplotlib.</p>"
        )

    def closeEvent(self, event):
        self.refresh_timer.stop()
        logger.info("Application closing.")
        event.accept()