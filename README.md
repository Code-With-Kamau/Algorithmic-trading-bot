# 🚀 SMC Scalping Bot - High-Frequency Trading System

A professional-grade algorithmic trading bot implementing Smart Money Concepts (SMC) for scalping with MT5 integration and real-time web dashboard.

## 📋 Features

### Trading Strategy
- **Smart Money Concepts (SMC)** implementation:
  - Fair Value Gaps (FVG) detection
  - Order Block identification
  - Change of Character (CHOCH) analysis
  - Liquidity sweep detection
- **Technical Analysis**:
  - RSI for momentum confirmation
  - ATR for dynamic stop loss/take profit
  - EMA trend analysis
  - Volume confirmation
- **Risk Management**:
  - Fixed risk per trade (default 2%)
  - Dynamic position sizing
  - Maximum daily loss limit
  - Risk:Reward ratio validation (min 1.5:1)

### Trade Management
- **Auto breakeven** after specified pips in profit
- **Trailing stop loss** for trend-following
- **Partial position closing** at target R:R ratio
- **Multi-symbol support** with concurrent monitoring

### Monitoring & Control
- **Real-time web dashboard** (Flask-based)
- **SQLite database** for trade logging and analytics
- **Performance tracking** with win rate, profit metrics
- **Manual control** via web interface
- **Auto/Manual mode** toggle

## 🛠️ Installation

### Prerequisites
- Python 3.10 or higher
- MetaTrader 5 terminal installed
- Active MT5 trading account (demo or live)

### Setup Steps

1. **Clone or download** the project files

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your MT5 credentials and settings
```

4. **Initialize database**:
The database will be created automatically on first run.

5. **Run the bot**:
```bash
python main.py
```

6. **Access dashboard**:
Open your browser to `http://localhost:5000`

## 📁 Project Structure

```
scalper_bot/
├── main.py                      # Entry point
├── config/
│   ├── settings.py             # Configuration management
│   └── risk_management.py      # Risk calculation & validation
├── core/
│   ├── market_data.py          # MT5 data fetching
│   ├── strategy.py             # SMC trading logic
│   ├── order_execution.py      # Trade execution
│   └── trade_manager.py        # Position management
├── analysis/
│   ├── indicators.py           # Technical indicators
│   ├── smc_logic.py            # SMC detection algorithms
│   └── liquidity.py            # Liquidity analysis
├── database/
│   └── database.py             # SQLite operations
├── web/
│   ├── app.py                  # Flask application
│   └── templates/
│       └── dashboard.html      # Web interface
├── utils/
│   ├── logger_config.py        # Logging setup
│   └── helpers.py              # Utility functions
├── logs/                        # Log files (auto-created)
├── database/                    # SQLite database (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

## ⚙️ Configuration

### Key Settings (in .env)

**Risk Management**:
- `RISK_PERCENT`: Risk per trade (default: 2%)
- `MAX_DAILY_LOSS`: Maximum daily loss limit (default: 5%)
- `MAX_OPEN_TRADES`: Maximum concurrent positions (default: 3)
- `MIN_RISK_REWARD`: Minimum R:R ratio (default: 1.5)

**Strategy Parameters**:
- `TIMEFRAME`: Trading timeframe (M1, M5, M15, M30, H1, H4, D1)
- `SYMBOLS`: Trading symbols, comma-separated
- `RSI_PERIOD`: RSI calculation period (default: 14)
- `ATR_PERIOD`: ATR calculation period (default: 14)

**SMC Settings**:
- `FVG_MIN_SIZE`: Minimum FVG size in price (default: 0.0001)
- `ORDER_BLOCK_LOOKBACK`: Candles to look back for order blocks (default: 20)
- `LIQUIDITY_SWEEP_PIPS`: Sweep detection threshold (default: 5.0)

**Trade Management**:
- `USE_TRAILING_STOP`: Enable trailing stop (True/False)
- `TRAILING_STOP_PIPS`: Trailing distance in pips (default: 10)
- `BREAKEVEN_PIPS`: Move to breakeven after X pips profit (default: 10)
- `PARTIAL_CLOSE_PERCENT`: Percentage to close at target R:R (default: 50%)

## 🎯 Usage

### Starting the Bot

1. Ensure MT5 is running and logged in
2. Run `python main.py`
3. Bot will:
   - Connect to MT5
   - Initialize database
   - Start web dashboard
   - Begin trading loop

### Web Dashboard Features

- **Real-time account metrics**: Balance, equity, P/L
- **Open positions monitoring**: View and manage active trades
- **Trade history**: Complete log with profits/losses
- **Performance statistics**: Win rate, total profit, averages
- **Control panel**:
  - Toggle AUTO/MANUAL mode
  - Close individual positions
  - Close all positions
  - Real-time status updates

### Trading Modes

**AUTO Mode**: Bot actively scans for signals and executes trades automatically

**MANUAL Mode**: Bot monitoring only, no automatic trade execution

## 📊 Trading Logic

### Signal Detection Process

1. **Market Data Collection**: Fetch OHLCV data for configured symbols
2. **Indicator Calculation**: RSI, ATR, EMAs, volume ratios
3. **SMC Analysis**:
   - Detect liquidity sweeps
   - Identify Fair Value Gaps
   - Find order blocks
   - Check for CHOCH
4. **Signal Scoring**: Weight different components
5. **Direction Determination**: Bullish/bearish based on confluence
6. **Trade Confirmation**:
   - Risk:Reward validation
   - Spread check
   - Daily loss limit check
   - Maximum positions check
7. **Execution**: Place order with calculated SL/TP

### Trade Management Flow

1. **Entry**: Position opened with SL and TP
2. **Monitoring**: Continuous position tracking
3. **Breakeven**: Move SL to breakeven + buffer after target profit
4. **Partial Close**: Close 50% at 1:1 R:R (configurable)
5. **Trailing Stop**: Trail SL as position moves in profit
6. **Exit**: Close at TP, SL, or manual intervention

## 📈 Performance Metrics

The bot tracks:
- Total trades executed
- Win rate percentage
- Total profit/loss
- Average profit per trade
- Maximum win/loss
- Daily P/L
- Equity curve

All metrics viewable in:
- Web dashboard
- SQLite database
- Log files

## 🔒 Safety Features

- **Maximum daily loss limit**: Stops trading after threshold
- **Position size validation**: Ensures lot sizes within broker limits
- **Spread filtering**: Rejects trades with excessive spread
- **Risk:Reward minimum**: Only trades with favorable R:R
- **Connection monitoring**: Handles MT5 disconnections
- **Error handling**: Comprehensive try-catch blocks
- **Logging**: Complete audit trail

## ⚠️ Disclaimer

**This is educational software**. Trading forex and CFDs involves significant risk of loss. Past performance does not guarantee future results.

- Always test on a demo account first
- Never risk more than you can afford to lose
- Use appropriate position sizing
- Monitor bot performance regularly
- Understand the code before deploying with real money

## 🐛 Troubleshooting

### Bot won't connect to MT5
- Ensure MT5 is running and logged in
- Check credentials in .env file
- Verify MT5 allows algorithmic trading

### No trades being executed
- Check if in MANUAL mode (switch to AUTO)
- Verify symbols are available in MT5
- Check spread is acceptable (< 3 pips for scalping)
- Review log files for errors

### Dashboard not loading
- Ensure Flask port 5000 is not blocked
- Check firewall settings
- Review console for Flask errors

## 📝 License

This project is provided as-is for educational purposes.


## 🤝 Contributing

This is a complete production system. Customize the strategy logic in `core/strategy.py` and SMC detection in `analysis/smc_logic.py` to fit your trading style.

## 📧 Support

Review logs in `logs/trading_bot.log` for debugging. All trade activity is logged to SQLite database for analysis.

---

**Built with**: Python, MetaTrader 5, Flask, SQLite, pandas

**Strategy**: Smart Money Concepts + Technical Analysis

**Risk**: Always use proper risk management and test thoroughly before live trading.