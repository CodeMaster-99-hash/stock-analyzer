"""
Stock Market Analyzer — Entry Point
=====================================
Handles both normal Python execution and
PyInstaller packaged .exe mode.
"""

import sys
import os

# ── Path resolution for PyInstaller ──────────────────────────
# When frozen (running as .exe), sys._MEIPASS contains the
# path to the temp directory where PyInstaller extracted files.
# When running normally, we use the script's directory.
if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    BASE_DIR = sys._MEIPASS
    APP_DIR  = os.path.dirname(sys.executable)
else:
    # Running as normal Python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR  = BASE_DIR

sys.path.insert(0, BASE_DIR)

# ── DPI scaling ───────────────────────────────────────────────
os.environ["QT_ENABLE_HIGHDPI_SCALING"]   = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# ── Load environment variables ────────────────────────────────
from dotenv import load_dotenv

# Look for .env next to the exe first, then in BASE_DIR
env_path = os.path.join(APP_DIR, '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(BASE_DIR, '.env')

load_dotenv(env_path)

from services.logging_service import setup_logging
from database.connection import DatabaseConnection


def main():
    setup_logging()

    import logging
    logger = logging.getLogger(__name__)
    logger.info("Starting Stock Market Analyzer...")
    logger.info(f"BASE_DIR : {BASE_DIR}")
    logger.info(f"APP_DIR  : {APP_DIR}")
    logger.info(f"Frozen   : {getattr(sys, 'frozen', False)}")

    # Initialise database
    try:
        DatabaseConnection.initialise()
        logger.info("Database ready.")
    except Exception as e:
        logger.critical(f"Database connection failed: {e}")

        # Show a user-friendly error dialog even before the
        # main window launches — much better than a silent crash
        from PyQt6.QtWidgets import QApplication, QMessageBox
        _app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Database Connection Failed",
            f"Could not connect to MySQL.\n\n"
            f"Error: {e}\n\n"
            f"Please check your .env file and ensure MySQL is running.\n"
            f"Expected .env location: {env_path}"
        )
        sys.exit(1)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from gui.windows.main_window import MainWindow

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Stock Market Analyzer")
    app.setOrganizationName("StockAnalyzer")
    app.setStyle("Fusion")

    # Load dark theme — look in BASE_DIR for packaged mode
    theme_path = os.path.join(
        BASE_DIR, 'resources', 'themes', 'dark_theme.qss'
    )
    if os.path.exists(theme_path):
        with open(theme_path, 'r') as f:
            app.setStyleSheet(f.read())
        logger.info("Dark theme loaded.")
    else:
        logger.warning(f"Theme not found at: {theme_path}")

    window = MainWindow()
    window.show()

    logger.info("GUI launched successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()