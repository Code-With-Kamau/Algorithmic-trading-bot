# 🚀 Quick Start Guide - SMC Scalping Bot

Get your trading bot up and running in 5 minutes!

## 📦 Prerequisites Checklist

- [ ] Python 3.10+ installed
- [ ] MetaTrader 5 terminal installed
- [ ] Active MT5 account (demo recommended for testing)
- [ ] MT5 terminal is running and logged in

## ⚡ Installation (5 Minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
# Use any text editor (notepad, nano, vim, vscode, etc.)
nano .env
```

### Step 3: Update .env File
Edit these critical settings:
```bash
# Your MT5 login credentials
MT5_LOGIN=12345678              # Your MT5 account number
MT5_PASSWORD=YourPassword123    # Your MT5 password
MT5_SERVER=MetaQuotes-Demo      # Your broker's server name

# Trading symbols (comma-separated, no spaces)
SYMBOLS=EURUSD,GBPUSD,USDJPY

# Risk per trade (recommended: 1-2% for testing)
RISK_PERCENT=2.0

# Maximum open trades
MAX_OPEN_TRADES=3
```

### Step 4: Run the Bot
```bash
python main.py
```

### Step 5: Open Dashboard
Open your browser and navigate to:
```
http://localhost:5000
```

## 🎯 First Run Checklist

After starting the bot, verify:

1. **Console Output**: Should show "MT5 connection successful"
2. **Dashboard Loads**: Browser shows the dashboard at localhost:5000
3. **Account Balance**: Dashboard displays your account balance
4. **Bot Status**: Shows "RUNNING" and "AUTO MODE"

## 🛡️ Safety First - Testing Mode

### For First Time Users:

1. **Use DEMO Account Only**
   - Never test on live account first
   - Open a demo account with your broker

2. **Start with Low Risk**
   ```bash
   RISK_PERCENT=0.5  # Use 0.5% for testing
   MAX_OPEN_TRADES=1 # Limit to 1 position
   ```

3. **Monitor Closely**
   - Watch the first few trades
   - Check log files in `logs/trading_bot.log`
   - Review database in `database/trades.db`

4. **Use Manual Mode**
   - Toggle to MANUAL mode via dashboard
   - Review signals without auto-execution
   - Switch to AUTO when comfortable

## 📊 Understanding the Dashboard

### Main Sections:

1. **Header (Purple)**
   - Bot status: RUNNING/STOPPED
   - Mode: AUTO/MANUAL
   - Control buttons

2. **Statistics Cards**
   - Account Balance & Equity
   - Today's P/L (profit/loss)
   - 30-day Win Rate
   - Total Profit

3. **Open Positions**
   - Real-time position monitoring
   - Current P/L for each trade
   - Close button for each position

4. **Trade History**
   - Last 50 closed trades
   - Profit/loss per trade
   - Entry/exit prices

### Control Buttons:

- **Toggle Mode**: Switch between AUTO and MANUAL
- **Close All Positions**: Emergency close all trades
- **Close (per trade)**: Close individual positions

## 🔧 Common Issues & Solutions

### Issue 1: "MT5 initialization failed"
**Solution:**
- Ensure MT5 terminal is running
- Check if you're logged into MT5
- Verify credentials in .env file
- Check MT5 server name is correct

### Issue 2: "No data received for symbol"
**Solution:**
- Right-click symbol in MT5 Market Watch
- Select "Show" to make it visible
- Check symbol spelling in .env matches MT5

### Issue 3: Dashboard won't load
**Solution:**
- Check if port 5000 is available
- Look for Flask errors in console
- Try accessing 127.0.0.1:5000 instead of localhost:5000

### Issue 4: No trades being executed
**Solution:**
- Check if bot is in MANUAL mode (switch to AUTO)
- Verify spread is acceptable (< 3 pips)
- Check log files for rejection reasons
- Ensure market is open

### Issue 5: "Permission denied" errors
**Solution:**
- Run terminal as administrator (Windows)
- Check file permissions on logs/ and database/ folders
- Ensure MT5 allows algorithmic trading

## 📝 Configuration Tips

### For Scalping (Fast Trading):
```bash
TIMEFRAME=M1
RISK_PERCENT=1.0
TRAILING_STOP_PIPS=5.0
BREAKEVEN_PIPS=5.0
```

### For Conservative Trading:
```bash
TIMEFRAME=M15
RISK_PERCENT=0.5
MAX_OPEN_TRADES=2
MIN_RISK_REWARD=2.0
```

### For Multiple Symbols:
```bash
SYMBOLS=EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD
MAX_OPEN_TRADES=5
```

## 📈 Monitoring Your Bot

### Check Logs:
```bash
# Real-time log monitoring (Linux/Mac)
tail -f logs/trading_bot.log

# On Windows, open in notepad
notepad logs/trading_bot.log
```

### Database Queries:
```bash
# View trades in SQLite (requires sqlite3)
sqlite3 database/trades.db "SELECT * FROM trades ORDER BY open_time DESC LIMIT 10;"
```

### Performance Check:
- Review dashboard every hour
- Check daily P/L
- Monitor win rate (target: >50%)
- Verify risk management is working

## 🎓 Learning Resources

### Understanding the Strategy:
1. Read about Smart Money Concepts (SMC)
2. Study Fair Value Gaps (FVG)
3. Learn Order Block theory
4. Understand liquidity sweeps

### Customization:
- Edit `core/strategy.py` for signal logic
- Modify `analysis/smc_logic.py` for SMC detection
- Adjust weights in `ScalpingStrategy` class

## ⚠️ Important Reminders

1. **This is a trading bot - it can lose money**
2. **Always test on demo first**
3. **Never risk more than you can afford to lose**
4. **Monitor the bot regularly**
5. **Understand the code before using**
6. **Keep logs for analysis**
7. **Back up your database regularly**

## 🆘 Getting Help

If you encounter issues:

1. Check `logs/trading_bot.log` for errors
2. Review the main README.md
3. Verify all prerequisites are met
4. Test MT5 connection manually
5. Review the test files for examples

## 🎉 Success Indicators

You know it's working when:
- ✅ Bot connects to MT5 successfully
- ✅ Dashboard shows real-time data
- ✅ Signals are being detected and logged
- ✅ Trades execute without errors
- ✅ Stop loss and take profit are set correctly
- ✅ Positions are managed automatically

## 🚦 Next Steps

After successful setup:

1. **Run for 24 hours** in demo mode
2. **Review all trades** in the database
3. **Analyze performance** metrics
4. **Adjust parameters** based on results
5. **Document your settings** that work best
6. **Only then consider** live trading (with extreme caution)

---

**Ready to start?** Run `python main.py` and watch the magic happen! 🎯

Remember: Trading involves risk. This bot is for educational purposes. Always use proper risk management!