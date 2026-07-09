## ⬇️ Download

[![Download](https://img.shields.io/github/v/release/CodeMaster-99-hash/stock-analyzer?label=Download&style=for-the-badge)](https://github.com/CodeMaster-99-hash/stock-analyzer/releases/latest)

**Windows 10/11 · No Python installation required**

---


\# 📈 Stock Market Analyzer



A professional desktop stock market analysis application built with Python, PyQt6, and MySQL. Features real-time data, technical analysis, ML-powered price prediction, portfolio management, and a dark-themed GUI.



\---



\## 🖥️ Screenshots



> Dashboard with live watchlist prices, technical charts, and AI prediction panel.



\---



\## ✨ Features



| Category | Features |

|----------|---------|

| \*\*Market Data\*\* | Real-time quotes, historical OHLCV prices, company info |

| \*\*Technical Analysis\*\* | SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP |

| \*\*Charts\*\* | Interactive price charts, RSI chart, MACD chart, volume bars |

| \*\*Portfolio\*\* | Buy/sell transactions, P\&L calculation, holdings tracking |

| \*\*Watchlist\*\* | Multi-stock monitoring with live price updates |

| \*\*ML Prediction\*\* | Linear Regression, Random Forest, XGBoost price prediction |

| \*\*Alerts\*\* | Price threshold alerts (above/below/percent change) |

| \*\*Settings\*\* | API key configuration, refresh intervals, theme |

| \*\*Export\*\* | Excel, CSV, PDF report generation |



\---



\## 🛠️ Tech Stack



| Layer | Technology |

|-------|-----------|

| Language | Python 3.12+ |

| GUI | PyQt6 |

| Database | MySQL 8.0 |

| Data | yfinance, Alpha Vantage, Finnhub |

| Analysis | Pandas, NumPy |

| Visualization | Matplotlib, Seaborn |

| ML | scikit-learn, XGBoost |

| NLP | TextBlob |

| Packaging | PyInstaller |

| Testing | Pytest |



\---



\## 🏗️ Architecture



\---



\## 🚀 Quick Start



\### Prerequisites



\- Python 3.12+

\- MySQL 8.0+

\- Git



\### Installation



\*\*1. Clone the repository\*\*



```bash

git clone https://github.com/yourusername/stock\_analyzer.git

cd stock\_analyzer

```



\*\*2. Create and activate virtual environment\*\*



```bash

\# Windows

python -m venv venv

venv\\Scripts\\activate

```



\*\*3. Install dependencies\*\*



```bash

pip install -r requirements.txt

```



\*\*4. Configure environment\*\*



```bash

copy .env.example .env

```



Open `.env` and fill in your MySQL credentials and API keys.



\*\*5. Set up the database\*\*



```bash

mysql -u root -p < database\\schema.sql

mysql -u root -p stock\_analyzer < database\\seed.sql

```



\*\*6. Fetch initial stock data\*\*



```bash

python scripts\\seed\_stock\_data.py

```



\*\*7. Train ML models\*\*



```bash

python scripts\\train\_models.py

```



\*\*8. Launch the application\*\*



```bash

python main.py

```



\---



\## 🔑 API Keys



The app works with free tier keys from:



| Provider | URL | Used For |

|----------|-----|---------|

| Alpha Vantage | https://alphavantage.co | Technical indicators |

| Finnhub | https://finnhub.io | News and sentiment |



Add keys to your `.env` file. The app functions without them using Yahoo Finance as the primary data source.



\---



\## 🧪 Running Tests



```bash

\# Run all tests

pytest



\# Run with coverage report

pytest --cov=. --cov-report=term-missing



\# Run a specific test file

pytest tests/test\_technical\_indicators.py -v

```



\---



\## 📦 Building the Executable



```bash

pyinstaller StockAnalyzer.spec

copy .env dist\\StockAnalyzer\\.env

dist\\StockAnalyzer\\StockAnalyzer.exe

```



\---



\## 🗄️ Database Schema



15 normalized MySQL tables covering:

`users` · `stocks` · `historical\_prices` · `watchlists` · `watchlist\_items` · `portfolio` · `transactions` · `alerts` · `predictions` · `technical\_indicators` · `news` · `settings` · `api\_cache` · `logs`



\---



\## 📐 Design Patterns Used



\- \*\*MVC\*\* — Models, Views (GUI), Controllers

\- \*\*Repository Pattern\*\* — Database access isolated in repository classes

\- \*\*Service Layer\*\* — Business logic separated from GUI and database

\- \*\*Dependency Injection\*\* — Services receive repositories via constructor

\- \*\*Singleton\*\* — Database connection pool

\- \*\*Adapter Pattern\*\* — API clients wrap external libraries

\- \*\*Strategy Pattern\*\* — Swappable ML models



\---



\## 🤝 Contributing



1\. Fork the repository

2\. Create a feature branch (`git checkout -b feature/your-feature`)

3\. Commit changes (`git commit -m 'Add your feature'`)

4\. Push to branch (`git push origin feature/your-feature`)

5\. Open a Pull Request



\---



\## 📄 License



MIT License — see `LICENSE` file for details.



\---



\## 👤 Author



\*\*Your Name\*\*

\- GitHub: \[@yourusername](https://github.com/yourusername)

\- LinkedIn: \[Your LinkedIn](https://linkedin.com/in/yourprofile)

