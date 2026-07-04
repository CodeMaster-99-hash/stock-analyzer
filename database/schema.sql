-- ============================================================
-- Stock Market Analyzer — Database Schema
-- ============================================================
-- Run this file with:
--   mysql -u root -p stock_analyzer < database\schema.sql
-- ============================================================

USE stock_analyzer;

-- ============================================================
-- TABLE: users
-- Stores application user accounts.
-- One user can have many watchlists, portfolios, and alerts.
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            INT           NOT NULL AUTO_INCREMENT,
    username      VARCHAR(50)   NOT NULL,
    email         VARCHAR(120)  NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email    (email),
    UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: stocks
-- Master list of every stock symbol we track.
-- All price and analysis tables reference this via stock_id.
-- ============================================================
CREATE TABLE IF NOT EXISTS stocks (
    id            INT           NOT NULL AUTO_INCREMENT,
    symbol        VARCHAR(10)   NOT NULL,
    name          VARCHAR(200)  NOT NULL,
    sector        VARCHAR(100),
    industry      VARCHAR(100),
    exchange      VARCHAR(20),
    country       VARCHAR(50),
    currency      VARCHAR(10)   NOT NULL DEFAULT 'USD',
    market_cap    DECIMAL(20,2),
    pe_ratio      DECIMAL(10,4),
    dividend_yield DECIMAL(8,4),
    week_52_high  DECIMAL(12,4),
    week_52_low   DECIMAL(12,4),
    description   TEXT,
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    last_updated  DATETIME,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_stocks_symbol (symbol),
    INDEX idx_stocks_sector   (sector),
    INDEX idx_stocks_exchange  (exchange)
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: historical_prices
-- Daily OHLCV data for each stock.
-- OHLCV = Open, High, Low, Close, Volume.
-- This is the core data table — it will have millions of rows.
-- Indexes on (stock_id, price_date) are critical for performance.
-- ============================================================
CREATE TABLE IF NOT EXISTS historical_prices (
    id            INT           NOT NULL AUTO_INCREMENT,
    stock_id      INT           NOT NULL,
    price_date    DATE          NOT NULL,
    open_price    DECIMAL(12,4) NOT NULL,
    high_price    DECIMAL(12,4) NOT NULL,
    low_price     DECIMAL(12,4) NOT NULL,
    close_price   DECIMAL(12,4) NOT NULL,
    adj_close     DECIMAL(12,4),
    volume        BIGINT        NOT NULL DEFAULT 0,

    PRIMARY KEY (id),
    UNIQUE KEY uq_price_stock_date (stock_id, price_date),
    INDEX idx_prices_date          (price_date),
    CONSTRAINT fk_prices_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: watchlists
-- A named list of stocks a user wants to monitor.
-- One user can have many watchlists (e.g. "Tech Stocks", "Dividends").
-- ============================================================
CREATE TABLE IF NOT EXISTS watchlists (
    id            INT           NOT NULL AUTO_INCREMENT,
    user_id       INT           NOT NULL,
    name          VARCHAR(100)  NOT NULL,
    description   VARCHAR(255),
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_watchlists_user (user_id),
    CONSTRAINT fk_watchlists_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: watchlist_items
-- Junction table linking watchlists to stocks.
-- A watchlist can contain many stocks.
-- A stock can appear in many watchlists.
-- This is a classic many-to-many relationship.
-- ============================================================
CREATE TABLE IF NOT EXISTS watchlist_items (
    id            INT           NOT NULL AUTO_INCREMENT,
    watchlist_id  INT           NOT NULL,
    stock_id      INT           NOT NULL,
    sort_order    INT           NOT NULL DEFAULT 0,
    added_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_watchlist_stock (watchlist_id, stock_id),
    CONSTRAINT fk_wi_watchlist
        FOREIGN KEY (watchlist_id) REFERENCES watchlists(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_wi_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: portfolio
-- A named investment portfolio belonging to a user.
-- One user can have multiple portfolios (e.g. "Retirement", "Growth").
-- ============================================================
CREATE TABLE IF NOT EXISTS portfolio (
    id            INT           NOT NULL AUTO_INCREMENT,
    user_id       INT           NOT NULL,
    name          VARCHAR(100)  NOT NULL,
    description   VARCHAR(255),
    currency      VARCHAR(10)   NOT NULL DEFAULT 'USD',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_portfolio_user (user_id),
    CONSTRAINT fk_portfolio_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: transactions
-- Every buy or sell action recorded against a portfolio.
-- The portfolio value is always CALCULATED from transactions —
-- we never store a "current value" directly (it would go stale).
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    id            INT           NOT NULL AUTO_INCREMENT,
    portfolio_id  INT           NOT NULL,
    stock_id      INT           NOT NULL,
    type          ENUM('BUY','SELL') NOT NULL,
    quantity      DECIMAL(14,6) NOT NULL,
    price         DECIMAL(12,4) NOT NULL,
    fees          DECIMAL(10,4) NOT NULL DEFAULT 0.00,
    notes         VARCHAR(255),
    trans_date    DATETIME      NOT NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_transactions_portfolio (portfolio_id),
    INDEX idx_transactions_stock     (stock_id),
    INDEX idx_transactions_date      (trans_date),
    CONSTRAINT fk_trans_portfolio
        FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_trans_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: alerts
-- Price alerts set by users for specific stocks.
-- The alert engine checks these on each price refresh.
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    id            INT           NOT NULL AUTO_INCREMENT,
    user_id       INT           NOT NULL,
    stock_id      INT           NOT NULL,
    alert_condition ENUM('ABOVE','BELOW','PERCENT_CHANGE') NOT NULL,
    target_price  DECIMAL(12,4),
    percent_value DECIMAL(8,4),
    message       VARCHAR(255),
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    triggered_at  DATETIME,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_alerts_user    (user_id),
    INDEX idx_alerts_stock   (stock_id),
    INDEX idx_alerts_active  (is_active),
    CONSTRAINT fk_alerts_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_alerts_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: predictions
-- ML model output — predicted future prices per stock.
-- Stores which model made the prediction and its confidence.
-- ============================================================
CREATE TABLE IF NOT EXISTS predictions (
    id              INT           NOT NULL AUTO_INCREMENT,
    stock_id        INT           NOT NULL,
    model_name      VARCHAR(50)   NOT NULL,
    predicted_price DECIMAL(12,4) NOT NULL,
    prediction_date DATE          NOT NULL,
    horizon_days    INT           NOT NULL DEFAULT 7,
    confidence      DECIMAL(5,4),
    mae             DECIMAL(10,4),
    rmse            DECIMAL(10,4),
    r2_score        DECIMAL(8,6),
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_predictions_stock (stock_id),
    INDEX idx_predictions_date  (prediction_date),
    CONSTRAINT fk_predictions_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: technical_indicators
-- Pre-calculated technical analysis values per stock per date.
-- Storing these avoids recalculating on every GUI load.
-- ============================================================
CREATE TABLE IF NOT EXISTS technical_indicators (
    id            INT           NOT NULL AUTO_INCREMENT,
    stock_id      INT           NOT NULL,
    calc_date     DATE          NOT NULL,
    rsi_14        DECIMAL(8,4),
    macd          DECIMAL(12,6),
    macd_signal   DECIMAL(12,6),
    macd_hist     DECIMAL(12,6),
    bb_upper      DECIMAL(12,4),
    bb_middle     DECIMAL(12,4),
    bb_lower      DECIMAL(12,4),
    sma_20        DECIMAL(12,4),
    sma_50        DECIMAL(12,4),
    sma_200       DECIMAL(12,4),
    ema_12        DECIMAL(12,4),
    ema_26        DECIMAL(12,4),
    vwap          DECIMAL(12,4),
    atr_14        DECIMAL(12,4),

    PRIMARY KEY (id),
    UNIQUE KEY uq_indicators_stock_date (stock_id, calc_date),
    CONSTRAINT fk_indicators_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: news
-- News headlines fetched for each stock with sentiment scores.
-- sentiment_score: -1.0 (very negative) to +1.0 (very positive)
-- ============================================================
CREATE TABLE IF NOT EXISTS news (
    id              INT           NOT NULL AUTO_INCREMENT,
    stock_id        INT,
    headline        VARCHAR(500)  NOT NULL,
    summary         TEXT,
    source          VARCHAR(100),
    url             VARCHAR(1000),
    sentiment_score DECIMAL(5,4),
    sentiment_label ENUM('POSITIVE','NEUTRAL','NEGATIVE'),
    published_at    DATETIME,
    fetched_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_news_stock       (stock_id),
    INDEX idx_news_published   (published_at),
    INDEX idx_news_sentiment   (sentiment_label),
    CONSTRAINT fk_news_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: settings
-- One row per user — application preferences.
-- One-to-one with users (each user has exactly one settings row).
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    id                  INT           NOT NULL AUTO_INCREMENT,
    user_id             INT           NOT NULL,
    theme               ENUM('DARK','LIGHT') NOT NULL DEFAULT 'DARK',
    default_currency    VARCHAR(10)   NOT NULL DEFAULT 'USD',
    refresh_interval    INT           NOT NULL DEFAULT 60,
    show_notifications  BOOLEAN       NOT NULL DEFAULT TRUE,
    decimal_places      INT           NOT NULL DEFAULT 2,
    date_format         VARCHAR(20)   NOT NULL DEFAULT 'YYYY-MM-DD',

    PRIMARY KEY (id),
    UNIQUE KEY uq_settings_user (user_id),
    CONSTRAINT fk_settings_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: api_cache
-- Stores raw API responses temporarily to avoid rate limits.
-- The application checks here before making any API call.
-- ============================================================
CREATE TABLE IF NOT EXISTS api_cache (
    id            INT           NOT NULL AUTO_INCREMENT,
    cache_key     VARCHAR(255)  NOT NULL,
    response_data LONGTEXT      NOT NULL,
    cached_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at    DATETIME      NOT NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uq_cache_key  (cache_key),
    INDEX idx_cache_expires  (expires_at)
) ENGINE=InnoDB;


-- ============================================================
-- TABLE: logs
-- Application event log written by Python's logging module.
-- Stored in DB so we can query and display logs in the GUI.
-- ============================================================
CREATE TABLE IF NOT EXISTS logs (
    id            INT           NOT NULL AUTO_INCREMENT,
    level         ENUM('DEBUG','INFO','WARNING','ERROR','CRITICAL') NOT NULL,
    message       TEXT          NOT NULL,
    module        VARCHAR(100),
    function_name VARCHAR(100),
    line_number   INT,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_logs_level    (level),
    INDEX idx_logs_created  (created_at),
    INDEX idx_logs_module   (module)
) ENGINE=InnoDB;