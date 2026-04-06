-- Trading Signals Table
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    entry_price REAL NOT NULL,
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    score REAL NOT NULL,
    components TEXT,
    executed BOOLEAN DEFAULT 0,
    INDEX idx_signals_timestamp (timestamp),
    INDEX idx_signals_symbol (symbol)
);

-- Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket INTEGER UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    type VARCHAR(10) NOT NULL,
    volume REAL NOT NULL,
    open_price REAL NOT NULL,
    close_price REAL,
    sl REAL NOT NULL,
    tp REAL NOT NULL,
    open_time DATETIME NOT NULL,
    close_time DATETIME,
    profit REAL,
    magic INTEGER,
    comment TEXT,
    signal_score REAL,
    close_reason TEXT,
    INDEX idx_trades_ticket (ticket),
    INDEX idx_trades_symbol (symbol),
    INDEX idx_trades_open_time (open_time),
    INDEX idx_trades_close_time (close_time)
);

-- Performance Metrics Table
CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_profit REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    INDEX idx_performance_date (date)
);

-- System Logs Table
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    INDEX idx_logs_timestamp (timestamp),
    INDEX idx_logs_level (level)
);

-- Views for Analytics

-- Daily Performance View
CREATE VIEW IF NOT EXISTS v_daily_performance AS
SELECT 
    DATE(close_time) as trade_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades,
    SUM(profit) as daily_profit,
    AVG(profit) as avg_profit,
    MAX(profit) as max_win,
    MIN(profit) as max_loss
FROM trades
WHERE close_time IS NOT NULL
GROUP BY DATE(close_time)
ORDER BY trade_date DESC;

-- Symbol Performance View
CREATE VIEW IF NOT EXISTS v_symbol_performance AS
SELECT 
    symbol,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winners,
    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losers,
    ROUND(SUM(CASE WHEN profit > 0 THEN 1.0 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit
FROM trades
WHERE close_time IS NOT NULL
GROUP BY symbol
ORDER BY total_profit DESC;

-- Recent Trades View
CREATE VIEW IF NOT EXISTS v_recent_trades AS
SELECT 
    ticket,
    symbol,
    type,
    volume,
    open_price,
    close_price,
    profit,
    open_time,
    close_time,
    close_reason,
    CASE 
        WHEN profit > 0 THEN 'WIN'
        WHEN profit < 0 THEN 'LOSS'
        ELSE 'BREAKEVEN'
    END as outcome
FROM trades
WHERE close_time IS NOT NULL
ORDER BY close_time DESC
LIMIT 100;