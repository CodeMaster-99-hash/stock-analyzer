USE stock_analyzer;

INSERT IGNORE INTO users (username, email, password_hash)
VALUES ('default_user', 'user@stockanalyzer.com', 'PLACEHOLDER_HASH');

INSERT IGNORE INTO stocks (symbol, name, sector, exchange, currency) VALUES
('AAPL',  'Apple Inc.',            'Technology',         'NASDAQ', 'USD'),
('MSFT',  'Microsoft Corporation', 'Technology',         'NASDAQ', 'USD'),
('GOOGL', 'Alphabet Inc.',         'Technology',         'NASDAQ', 'USD'),
('AMZN',  'Amazon.com Inc.',       'Consumer Cyclical',  'NASDAQ', 'USD'),
('TSLA',  'Tesla Inc.',            'Consumer Cyclical',  'NASDAQ', 'USD'),
('NVDA',  'NVIDIA Corporation',    'Technology',         'NASDAQ', 'USD'),
('META',  'Meta Platforms Inc.',   'Technology',         'NASDAQ', 'USD'),
('JPM',   'JPMorgan Chase & Co.', 'Financial Services', 'NYSE',   'USD'),
('JNJ',   'Johnson & Johnson',     'Healthcare',         'NYSE',   'USD'),
('V',     'Visa Inc.',             'Financial Services', 'NYSE',   'USD');

INSERT IGNORE INTO watchlists (user_id, name, description)
SELECT id, 'My Watchlist', 'Default watchlist'
FROM users WHERE username = 'default_user';

INSERT IGNORE INTO portfolio (user_id, name, description)
SELECT id, 'My Portfolio', 'Default portfolio'
FROM users WHERE username = 'default_user';

INSERT IGNORE INTO settings (user_id)
SELECT id FROM users WHERE username = 'default_user';